"""
test_host_service.py

Unit tests for provider-neutral host application services.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.secrets import EncryptedSecret, SecretEncryptor
from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.models import Host
from fourdrinier.db.schemas.host import DockerHostCreate, HostCreate, KubernetesHostCreate
from fourdrinier.hosts import (
    HostNameConflictError,
    HostNotFoundError,
    HostPingResult,
    HostProviderMismatchError,
    HostType,
)
from fourdrinier.hosts.drivers import HostDriver, HostDriverRegistry
from fourdrinier.hosts.service import HostService

_HOST_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000101")
_KEYPAIR_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000103")
_OBSERVED_AT: datetime = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class _CrudMocks:
    create_host: AsyncMock
    delete_host: AsyncMock
    get_host: AsyncMock
    list_hosts: AsyncMock


@pytest.fixture
def crud(monkeypatch: pytest.MonkeyPatch) -> _CrudMocks:
    """Replace host CRUD operations with isolated async test doubles.

    Args:
        monkeypatch: Pytest fixture used to replace CRUD functions for one test.

    Returns:
        The CRUD test doubles installed for the current test.
    """
    create_host: AsyncMock = AsyncMock(spec=hosts_crud.create_host)
    delete_host: AsyncMock = AsyncMock(spec=hosts_crud.delete_host)
    get_host: AsyncMock = AsyncMock(spec=hosts_crud.get_host)
    list_hosts: AsyncMock = AsyncMock(spec=hosts_crud.list_hosts)
    monkeypatch.setattr(hosts_crud, "create_host", create_host)
    monkeypatch.setattr(hosts_crud, "delete_host", delete_host)
    monkeypatch.setattr(hosts_crud, "get_host", get_host)
    monkeypatch.setattr(hosts_crud, "list_hosts", list_hosts)
    return _CrudMocks(
        create_host=create_host,
        delete_host=delete_host,
        get_host=get_host,
        list_hosts=list_hosts,
    )


def _service_dependencies() -> tuple[HostService, AsyncMock, Mock, Mock]:
    session: AsyncMock = AsyncMock(spec=AsyncSession)
    drivers: Mock = Mock(spec=HostDriverRegistry)
    secret_encryptor: Mock = Mock(spec=SecretEncryptor)
    service: HostService = HostService(
        session=cast(AsyncSession, session),
        drivers=cast(HostDriverRegistry, drivers),
        secret_encryptor=cast(SecretEncryptor, secret_encryptor),
    )
    return service, session, drivers, secret_encryptor


def _docker_request() -> DockerHostCreate:
    request: DockerHostCreate = DockerHostCreate(
        type="docker",
        name="docker-production",
        enabled=False,
        labels={"environment": "production"},
        address="203.0.113.10",
        port=2222,
        username="docker",
        keypair_id=_KEYPAIR_ID,
    )
    return request


def _kubernetes_request() -> KubernetesHostCreate:
    request: KubernetesHostCreate = KubernetesHostCreate.model_construct(
        type="kubernetes",
        name="kubernetes-production",
        enabled=True,
        labels={"environment": "production"},
        api_url="https://203.0.113.20:6443",
        ca_cert_pem="certificate",
        token="service-account-token",
        namespace="fourdrinier",
    )
    return request


def _host(host_type: HostType = HostType.DOCKER) -> Host:
    host: Host = Host(id=_HOST_ID, type=host_type, name="production")
    return host


async def test_host_service_create_001_nominal_docker_aggregate_is_committed(
    crud: _CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A Docker creation request declares matching provider details
    Result: A complete Docker aggregate is persisted and committed without encryption
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: DockerHostCreate = _docker_request()
    created: Host = _host()
    crud.create_host.return_value = created

    # Act
    result: Host = await service.create(request)

    # Assert
    persisted: Host = crud.create_host.await_args.args[1]
    assert result is created
    assert persisted.type is HostType.DOCKER
    assert persisted.name == request.name
    assert persisted.enabled is False
    assert persisted.labels == request.labels
    assert persisted.docker_details is not None
    assert persisted.docker_details.address == request.address
    assert persisted.docker_details.port == request.port
    assert persisted.docker_details.username == request.username
    assert persisted.docker_details.keypair_id == request.keypair_id
    assert persisted.kubernetes_details is None
    crud.create_host.assert_awaited_once_with(session, persisted)
    _secret_encryptor.encrypt.assert_not_called()
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_host_service_create_002_nominal_kubernetes_token_is_encrypted(
    crud: _CrudMocks,
) -> None:
    """Test 002 - Nominal
    Condition: A Kubernetes creation request contains plaintext credentials
    Result: Only encrypted credentials are attached to the committed Kubernetes aggregate
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: KubernetesHostCreate = _kubernetes_request()
    ciphertext: EncryptedSecret = EncryptedSecret(b"encrypted-token")
    created: Host = _host(HostType.KUBERNETES)
    crud.create_host.return_value = created
    _secret_encryptor.encrypt.return_value = ciphertext

    # Act
    result: Host = await service.create(request)

    # Assert
    persisted: Host = crud.create_host.await_args.args[1]
    assert result is created
    assert persisted.type is HostType.KUBERNETES
    assert persisted.docker_details is None
    assert persisted.kubernetes_details is not None
    assert persisted.kubernetes_details.api_url == request.api_url
    assert persisted.kubernetes_details.ca_cert_pem == request.ca_cert_pem
    assert persisted.kubernetes_details.token_encrypted == ciphertext
    assert persisted.kubernetes_details.namespace == request.namespace
    _secret_encryptor.encrypt.assert_called_once_with(b"service-account-token")
    crud.create_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    "error_message",
    [
        pytest.param(
            'duplicate key value violates unique constraint "uq_hosts_name"',
            id="named-constraint",
        ),
        pytest.param(
            "UNIQUE constraint failed: hosts.name",
            id="sqlite-constraint",
        ),
    ],
)
async def test_host_service_create_003_anomalous_duplicate_name_is_rejected(
    error_message: str,
    crud: _CrudMocks,
) -> None:
    """Test 003 - Anomalous
    Condition: Persistence rejects a host that duplicates an existing name
    Result: HostNameConflictError is raised after the transaction is rolled back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: DockerHostCreate = _docker_request()
    integrity_error: IntegrityError = IntegrityError(
        "insert host",
        {},
        RuntimeError(error_message),
    )
    crud.create_host.side_effect = integrity_error
    captured: pytest.ExceptionInfo[HostNameConflictError]

    # Act
    with pytest.raises(
        HostNameConflictError,
        match="host with name 'docker-production' already exists",
    ) as captured:
        await service.create(request)

    # Assert
    assert captured.value.provider is HostType.DOCKER
    assert captured.value.__cause__ is integrity_error
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("command", "provider", "message"),
    [
        pytest.param(
            DockerHostCreate.model_construct(
                **{**_docker_request().model_dump(), "type": "kubernetes"}
            ),
            HostType.DOCKER,
            "Docker host details must declare the docker provider",
            id="docker-details",
        ),
        pytest.param(
            KubernetesHostCreate.model_construct(
                **{**_kubernetes_request().model_dump(), "type": "docker"}
            ),
            HostType.KUBERNETES,
            "Kubernetes host details must declare the kubernetes provider",
            id="kubernetes-details",
        ),
    ],
)
async def test_host_service_create_004_anomalous_provider_details_do_not_match(
    command: DockerHostCreate | KubernetesHostCreate,
    provider: HostType,
    message: str,
    crud: _CrudMocks,
) -> None:
    """Test 004 - Anomalous
    Condition: Provider-specific creation details declare the other provider type
    Result: HostProviderMismatchError is raised before persistence and the transaction rolls back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    captured: pytest.ExceptionInfo[HostProviderMismatchError]

    # Act
    with pytest.raises(HostProviderMismatchError, match=message) as captured:
        await service.create(command)

    # Assert
    assert captured.value.provider is provider
    crud.create_host.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_create_005_anomalous_unknown_details_are_rejected(
    crud: _CrudMocks,
) -> None:
    """Test 005 - Anomalous
    Condition: The service receives details outside the validated creation union
    Result: HostProviderMismatchError identifies the unsupported details and rolls back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: HostCreate = cast(
        HostCreate,
        SimpleNamespace(name="unsupported", type="docker"),
    )

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="unsupported host creation details SimpleNamespace",
    ):
        await service.create(request)

    # Assert
    crud.create_host.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_create_006_anomalous_integrity_failure_is_rolled_back(
    crud: _CrudMocks,
) -> None:
    """Test 006 - Anomalous
    Condition: Persistence raises an IntegrityError unrelated to the host name constraint
    Result: The transaction rolls back and the original IntegrityError is propagated
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: DockerHostCreate = _docker_request()
    integrity_error: IntegrityError = IntegrityError(
        "insert host",
        {},
        RuntimeError("constraint failed"),
    )
    crud.create_host.side_effect = integrity_error

    # Act
    with pytest.raises(IntegrityError) as captured:
        await service.create(request)

    # Assert
    assert captured.value is integrity_error
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_create_007_anomalous_non_integrity_failure_is_rolled_back(
    crud: _CrudMocks,
) -> None:
    """Test 007 - Anomalous
    Condition: Persistence fails for a reason unrelated to a database constraint
    Result: The original exception is propagated after rolling back the transaction
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    request: DockerHostCreate = _docker_request()
    failure: RuntimeError = RuntimeError("database unavailable")
    crud.create_host.side_effect = failure

    # Act
    with pytest.raises(RuntimeError, match="database unavailable") as captured:
        await service.create(request)

    # Assert
    assert captured.value is failure
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_get_008_nominal_host_is_returned(crud: _CrudMocks) -> None:
    """Test 008 - Nominal
    Condition: Host persistence contains a host for the requested ID
    Result: The matching aggregate is returned without ending the read transaction
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    host: Host = _host()
    crud.get_host.return_value = host

    # Act
    result: Host = await service.get(_HOST_ID)

    # Assert
    assert result is host
    crud.get_host.assert_awaited_once_with(session, _HOST_ID)
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


async def test_host_service_get_009_anomalous_unknown_host_is_rejected(
    crud: _CrudMocks,
) -> None:
    """Test 009 - Anomalous
    Condition: Host persistence does not contain the requested host ID
    Result: HostNotFoundError identifies the missing host
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    crud.get_host.return_value = None

    # Act
    with pytest.raises(HostNotFoundError, match=f"host {_HOST_ID} not found"):
        await service.get(_HOST_ID)

    # Assert
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(None, id="all"),
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_host_service_list_010_nominal_provider_filter_is_forwarded(
    host_type: HostType | None,
    crud: _CrudMocks,
) -> None:
    """Test 010 - Nominal
    Condition: A caller supplies an optional provider filter
    Result: The ordered matching aggregate list is returned unchanged
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    hosts: list[Host] = [_host()]
    crud.list_hosts.return_value = hosts

    # Act
    result: list[Host] = await service.list(host_type)

    # Assert
    assert result is hosts
    crud.list_hosts.assert_awaited_once_with(session, host_type)
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


async def test_host_service_delete_011_nominal_host_is_deleted_and_committed(
    crud: _CrudMocks,
) -> None:
    """Test 011 - Nominal
    Condition: The requested host exists
    Result: Its aggregate is deleted and the transaction is committed
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    host: Host = _host()
    crud.get_host.return_value = host

    # Act
    result: None = await service.delete(_HOST_ID)

    # Assert
    assert result is None
    crud.delete_host.assert_awaited_once_with(session, host)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    ("persisted", "failure", "message"),
    [
        pytest.param(None, None, f"host {_HOST_ID} not found", id="missing-host"),
        pytest.param(_host(), RuntimeError("delete failed"), "delete failed", id="delete-failure"),
    ],
)
async def test_host_service_delete_012_anomalous_failure_is_rolled_back(
    persisted: Host | None,
    failure: RuntimeError | None,
    message: str,
    crud: _CrudMocks,
) -> None:
    """Test 012 - Anomalous
    Condition: The host is missing or its persistence deletion fails
    Result: The write transaction rolls back and the typed or original failure propagates
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    crud.get_host.return_value = persisted
    crud.delete_host.side_effect = failure
    expected_error: type[Exception] = HostNotFoundError if persisted is None else RuntimeError

    # Act
    with pytest.raises(expected_error, match=message):
        await service.delete(_HOST_ID)

    # Assert
    if persisted is None:
        crud.delete_host.assert_not_awaited()
    else:
        crud.delete_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_ping_013_nominal_observation_is_committed(
    crud: _CrudMocks,
) -> None:
    """Test 013 - Nominal
    Condition: A matching provider driver successfully checks the requested host
    Result: The observation time is persisted and the provider-neutral result is returned
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    host: Host = _host()
    driver: AsyncMock = AsyncMock(spec=HostDriver)
    ping_result: HostPingResult = HostPingResult(
        host_id=_HOST_ID,
        type=HostType.DOCKER,
        latency_ms=2.5,
        observed_at=_OBSERVED_AT,
    )
    crud.get_host.return_value = host
    _drivers.for_host.return_value = driver
    driver.ping.return_value = ping_result

    # Act
    result: HostPingResult = await service.ping(_HOST_ID)

    # Assert
    assert result is ping_result
    assert host.last_seen_at is _OBSERVED_AT
    _drivers.for_host.assert_called_once_with(host)
    driver.ping.assert_awaited_once_with(host)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_host_service_ping_014_anomalous_missing_host_is_rolled_back(
    crud: _CrudMocks,
) -> None:
    """Test 014 - Anomalous
    Condition: No host exists for the requested ping target
    Result: HostNotFoundError is raised without selecting a driver and the transaction rolls back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    crud.get_host.return_value = None

    # Act
    with pytest.raises(HostNotFoundError, match=f"host {_HOST_ID} not found"):
        await service.ping(_HOST_ID)

    # Assert
    _drivers.for_host.assert_not_called()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    "failure_source",
    [
        pytest.param("driver", id="driver-failure"),
        pytest.param("commit", id="commit-failure"),
    ],
)
async def test_host_service_ping_016_anomalous_operation_failure_is_rolled_back(
    failure_source: str,
    crud: _CrudMocks,
) -> None:
    """Test 016 - Anomalous
    Condition: The provider check or the local commit fails
    Result: The original failure propagates after the transaction is rolled back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = _service_dependencies()
    host: Host = _host()
    driver: AsyncMock = AsyncMock(spec=HostDriver)
    failure: RuntimeError = RuntimeError(f"{failure_source} failed")
    ping_result: HostPingResult = HostPingResult(
        host_id=_HOST_ID,
        type=HostType.DOCKER,
        latency_ms=2.5,
        observed_at=_OBSERVED_AT,
    )
    crud.get_host.return_value = host
    _drivers.for_host.return_value = driver
    driver.ping.return_value = ping_result
    if failure_source == "driver":
        driver.ping.side_effect = failure
    else:
        session.commit.side_effect = failure

    # Act
    with pytest.raises(RuntimeError, match=f"{failure_source} failed") as captured:
        await service.ping(_HOST_ID)

    # Assert
    assert captured.value is failure
    session.rollback.assert_awaited_once_with()
