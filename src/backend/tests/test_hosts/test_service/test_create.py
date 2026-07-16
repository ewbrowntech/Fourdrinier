"""
test_create.py

Unit tests for HostService.create.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.core.secrets import EncryptedSecret
from fourdrinier.db.models import Host
from fourdrinier.hosts import HostKeypairNotFoundError, HostNameConflictError, HostType
from fourdrinier.hosts.service import HostService
from fourdrinier.schemas.host import DockerHostCreate, KubernetesHostCreate
from tests.test_hosts.test_service.support import (
    KEYPAIR_ID,
    CrudMocks,
    docker_request,
    host,
    kubernetes_request,
    service_dependencies,
)


async def test_host_service_create_001_nominal_docker_aggregate_is_committed(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A Docker creation request declares matching provider details
    Result: A complete Docker aggregate is persisted and committed without encryption
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    secret_encryptor: Mock
    service, session, _drivers, secret_encryptor = service_dependencies()
    request: DockerHostCreate = docker_request()
    created: Host = host()
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
    crud.get_keypair.assert_awaited_once_with(session, KEYPAIR_ID)
    secret_encryptor.encrypt.assert_not_called()
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_host_service_create_002_nominal_kubernetes_token_is_encrypted(
    crud: CrudMocks,
) -> None:
    """Test 002 - Nominal
    Condition: A Kubernetes creation request contains plaintext credentials
    Result: Only encrypted credentials are attached to the committed Kubernetes aggregate
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    secret_encryptor: Mock
    service, session, _drivers, secret_encryptor = service_dependencies()
    request: KubernetesHostCreate = kubernetes_request()
    ciphertext: EncryptedSecret = EncryptedSecret(b"encrypted-token")
    created: Host = host(HostType.KUBERNETES)
    crud.create_host.return_value = created
    secret_encryptor.encrypt.return_value = ciphertext

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
    secret_encryptor.encrypt.assert_called_once_with(b"service-account-token")
    crud.create_host.assert_awaited_once_with(session, persisted)
    crud.get_keypair.assert_not_awaited()
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
    crud: CrudMocks,
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
    service, session, _drivers, _secret_encryptor = service_dependencies()
    request: DockerHostCreate = docker_request()
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


async def test_host_service_create_004_anomalous_integrity_failure_is_rolled_back(
    crud: CrudMocks,
) -> None:
    """Test 004 - Anomalous
    Condition: Persistence raises an IntegrityError unrelated to the host name constraint
    Result: The transaction rolls back and the original IntegrityError is propagated
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    request: DockerHostCreate = docker_request()
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


async def test_host_service_create_005_anomalous_non_integrity_failure_is_rolled_back(
    crud: CrudMocks,
) -> None:
    """Test 005 - Anomalous
    Condition: Persistence fails for a reason unrelated to a database constraint
    Result: The original exception is propagated after rolling back the transaction
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    request: DockerHostCreate = docker_request()
    failure: RuntimeError = RuntimeError("database unavailable")
    crud.create_host.side_effect = failure

    # Act
    with pytest.raises(RuntimeError, match="database unavailable") as captured:
        await service.create(request)

    # Assert
    assert captured.value is failure
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_create_006_anomalous_docker_keypair_does_not_exist(
    crud: CrudMocks,
) -> None:
    """Test 006 - Anomalous
    Condition: A Docker request selects an SSH keypair that does not exist
    Result: HostKeypairNotFoundError is raised before persistence and the transaction rolls back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    request: DockerHostCreate = docker_request()
    crud.get_keypair.return_value = None

    # Act
    with pytest.raises(
        HostKeypairNotFoundError,
        match=f"keypair {KEYPAIR_ID} not found",
    ) as captured:
        await service.create(request)

    # Assert
    assert captured.value.provider is HostType.DOCKER
    crud.create_host.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
