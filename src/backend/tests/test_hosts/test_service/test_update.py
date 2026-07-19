"""
test_update.py

Unit tests for HostService.update.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.core.secrets import EncryptedSecret
from fourdrinier.db.models import Host
from fourdrinier.hosts import (
    HostKeypairNotFoundError,
    HostNameConflictError,
    HostNotFoundError,
    HostType,
    HostTypeChangeError,
)
from fourdrinier.hosts.service import HostService
from fourdrinier.schemas.host import DockerHostUpdate, KubernetesHostUpdate
from tests.test_api.test_hosts.support import CA_PEM
from tests.test_hosts.test_service.support import (
    HOST_ID,
    KEYPAIR_ID,
    CrudMocks,
    host,
    service_dependencies,
)

NEW_KEYPAIR_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000104")


async def test_host_service_update_001_nominal_docker_fields_and_keypair_are_committed(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: Every mutable Docker field and its credential keypair are supplied
    Result: The complete aggregate is updated and committed without encrypting data
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    secret_encryptor: Mock
    service, session, _drivers, secret_encryptor = service_dependencies()
    persisted: Host = host()
    request: DockerHostUpdate = DockerHostUpdate(
        type="docker",
        name="docker-updated",
        enabled=False,
        labels={"environment": "staging"},
        address="203.0.113.10",
        port=2222,
        username="docker",
        keypair_id=NEW_KEYPAIR_ID,
    )
    crud.get_host.return_value = persisted
    crud.update_host.return_value = persisted

    # Act
    result: Host = await service.update(HOST_ID, request)

    # Assert
    assert result is persisted
    assert persisted.name == "docker-updated"
    assert persisted.enabled is False
    assert persisted.labels == {"environment": "staging"}
    assert persisted.docker_details is not None
    assert persisted.docker_details.address == "203.0.113.10"
    assert persisted.docker_details.port == 2222
    assert persisted.docker_details.username == "docker"
    assert persisted.docker_details.keypair_id == NEW_KEYPAIR_ID
    crud.get_keypair.assert_awaited_once_with(session, NEW_KEYPAIR_ID)
    crud.update_host.assert_awaited_once_with(session, persisted)
    secret_encryptor.encrypt.assert_not_called()
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_host_service_update_002_nominal_kubernetes_credential_is_encrypted(
    crud: CrudMocks,
) -> None:
    """Test 002 - Nominal
    Condition: Every mutable Kubernetes field includes a replacement plaintext token
    Result: Public fields and only the encrypted replacement credential are committed
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    secret_encryptor: Mock
    service, session, _drivers, secret_encryptor = service_dependencies()
    persisted: Host = host(HostType.KUBERNETES)
    request: KubernetesHostUpdate = KubernetesHostUpdate(
        type="kubernetes",
        name="kubernetes-updated",
        enabled=False,
        labels={"environment": "staging"},
        api_url="https://203.0.113.20:6443",
        ca_cert_pem=CA_PEM,
        token="replacement-token",
        namespace="fourdrinier",
    )
    ciphertext: EncryptedSecret = EncryptedSecret(b"replacement-token-encrypted")
    secret_encryptor.encrypt.return_value = ciphertext
    crud.get_host.return_value = persisted
    crud.update_host.return_value = persisted

    # Act
    result: Host = await service.update(HOST_ID, request)

    # Assert
    assert result is persisted
    assert persisted.kubernetes_details is not None
    assert persisted.kubernetes_details.api_url == "https://203.0.113.20:6443"
    assert persisted.kubernetes_details.ca_cert_pem == CA_PEM
    assert persisted.kubernetes_details.token_encrypted == ciphertext
    assert persisted.kubernetes_details.namespace == "fourdrinier"
    secret_encryptor.encrypt.assert_called_once_with(b"replacement-token")
    crud.get_keypair.assert_not_awaited()
    crud.update_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("persisted", "update_request", "expected_error", "message"),
    [
        pytest.param(
            None,
            DockerHostUpdate(type="docker"),
            HostNotFoundError,
            f"host {HOST_ID} not found",
            id="missing-host",
        ),
        pytest.param(
            host(),
            KubernetesHostUpdate(type="kubernetes"),
            HostTypeChangeError,
            f"host {HOST_ID} has type docker; type cannot be changed to kubernetes",
            id="type-change",
        ),
    ],
)
async def test_host_service_update_003_anomalous_host_cannot_be_updated(
    persisted: Host | None,
    update_request: DockerHostUpdate | KubernetesHostUpdate,
    expected_error: type[Exception],
    message: str,
    crud: CrudMocks,
) -> None:
    """Test 003 - Anomalous
    Condition: The host is absent or its persisted provider differs from the request
    Result: A typed error is raised and the transaction is rolled back without an update
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    crud.get_host.return_value = persisted

    # Act
    with pytest.raises(expected_error, match=message):
        await service.update(HOST_ID, update_request)

    # Assert
    crud.update_host.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_host_service_update_004_anomalous_keypair_does_not_exist(
    crud: CrudMocks,
) -> None:
    """Test 004 - Anomalous
    Condition: A Docker update selects an SSH keypair that does not exist
    Result: HostKeypairNotFoundError is raised and the update is rolled back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    persisted: Host = host()
    request: DockerHostUpdate = DockerHostUpdate(type="docker", keypair_id=NEW_KEYPAIR_ID)
    crud.get_host.return_value = persisted
    crud.get_keypair.return_value = None

    # Act
    with pytest.raises(
        HostKeypairNotFoundError,
        match=f"keypair {NEW_KEYPAIR_ID} not found",
    ):
        await service.update(HOST_ID, request)

    # Assert
    assert persisted.docker_details is not None
    assert persisted.docker_details.keypair_id == KEYPAIR_ID
    crud.update_host.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        pytest.param(
            IntegrityError(
                "update host",
                {},
                RuntimeError('duplicate key violates constraint "uq_hosts_name"'),
            ),
            HostNameConflictError,
            id="duplicate-name",
        ),
        pytest.param(
            IntegrityError("update host", {}, RuntimeError("constraint failed")),
            IntegrityError,
            id="other-integrity-error",
        ),
        pytest.param(RuntimeError("database unavailable"), RuntimeError, id="other-error"),
    ],
)
async def test_host_service_update_005_anomalous_persistence_failure_is_rolled_back(
    failure: Exception,
    expected_error: type[Exception],
    crud: CrudMocks,
) -> None:
    """Test 005 - Anomalous
    Condition: Persistence rejects the new name or fails for another reason
    Result: A name conflict or original failure is raised after rollback
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    persisted: Host = host()
    request: DockerHostUpdate = DockerHostUpdate(type="docker", name="duplicate")
    crud.get_host.return_value = persisted
    crud.update_host.side_effect = failure

    # Act
    with pytest.raises(expected_error):
        await service.update(HOST_ID, request)

    # Assert
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("host_type", "update_request"),
    [
        pytest.param(HostType.DOCKER, DockerHostUpdate(type="docker"), id="docker"),
        pytest.param(
            HostType.KUBERNETES,
            KubernetesHostUpdate(type="kubernetes"),
            id="kubernetes",
        ),
    ],
)
async def test_host_service_update_006_nominal_type_only_request_is_noop(
    host_type: HostType,
    update_request: DockerHostUpdate | KubernetesHostUpdate,
    crud: CrudMocks,
) -> None:
    """Test 006 - Nominal
    Condition: A matching update request supplies no mutable fields
    Result: The unchanged aggregate is flushed and committed
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    secret_encryptor: Mock
    service, session, _drivers, secret_encryptor = service_dependencies()
    persisted: Host = host(host_type)
    crud.get_host.return_value = persisted
    crud.update_host.return_value = persisted

    # Act
    result: Host = await service.update(HOST_ID, update_request)

    # Assert
    assert result is persisted
    crud.get_keypair.assert_not_awaited()
    secret_encryptor.encrypt.assert_not_called()
    crud.update_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
