"""
test_service.py

Unit tests for logical server persistence orchestration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerCreate, ServerUpdate
from fourdrinier.servers import (
    PUMPKIN_MINECRAFT_VERSION,
    ServerDesiredState,
    ServerNameConflictError,
    ServerNotFoundError,
    ServerRuntime,
)
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    SERVER_ID,
    CrudMocks,
    server,
    service_dependencies,
)


async def test_server_service_create_001_nominal_fixed_configuration_is_committed(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A valid Pumpkin server creation request is supplied
    Result: A stopped generation-one configuration is persisted and committed
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    request: ServerCreate = ServerCreate(name="lantern-grove")
    created: Server = server(request.name)
    crud.create_server.return_value = created

    # Act
    result: Server = await service.create(request)

    # Assert
    persisted: Server = crud.create_server.await_args.args[1]
    assert result is created
    assert persisted.name == request.name
    assert persisted.runtime is ServerRuntime.PUMPKIN
    assert persisted.minecraft_version == PUMPKIN_MINECRAFT_VERSION
    assert persisted.desired_state is ServerDesiredState.STOPPED
    assert persisted.spec_generation == 1
    crud.create_server.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        pytest.param(
            IntegrityError(
                "insert server",
                {},
                RuntimeError('duplicate key violates constraint "uq_servers_name"'),
            ),
            ServerNameConflictError,
            id="name-conflict",
        ),
        pytest.param(
            IntegrityError("insert server", {}, RuntimeError("constraint failed")),
            IntegrityError,
            id="other-integrity-failure",
        ),
        pytest.param(RuntimeError("database unavailable"), RuntimeError, id="database-failure"),
    ],
)
async def test_server_service_create_002_anomalous_failure_is_rolled_back(
    failure: Exception,
    expected_error: type[Exception],
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
    Condition: Persistence rejects the insert or becomes unavailable
    Result: A typed or original error is raised after the transaction rolls back
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    request: ServerCreate = ServerCreate(name="conflicted-world")
    crud.create_server.side_effect = failure

    # Act
    with pytest.raises(expected_error) as captured:
        await service.create(request)

    # Assert
    if expected_error is ServerNameConflictError:
        assert str(captured.value) == "server with name 'conflicted-world' already exists"
        assert captured.value.__cause__ is failure
    else:
        assert captured.value is failure
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_server_service_list_003_nominal_ordered_servers_are_forwarded(
    crud: CrudMocks,
) -> None:
    """Test 003 - Nominal
    Condition: Persistence returns its ordered logical server collection
    Result: The service returns that collection without opening a write transaction
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    persisted: list[Server] = [server()]
    crud.list_servers.return_value = persisted

    # Act
    result: list[Server] = await service.list()

    # Assert
    assert result is persisted
    crud.list_servers.assert_awaited_once_with(session)
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


async def test_server_service_get_004_nominal_server_is_returned(
    crud: CrudMocks,
) -> None:
    """Test 004 - Nominal
    Condition: Persistence contains the requested logical server
    Result: The service returns the matching logical server
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    persisted: Server = server()
    crud.get_server.return_value = persisted

    # Act
    result: Server = await service.get(SERVER_ID)

    # Assert
    assert result is persisted
    crud.get_server.assert_awaited_once_with(session, SERVER_ID)


async def test_server_service_get_005_anomalous_server_is_missing(
    crud: CrudMocks,
) -> None:
    """Test 005 - Anomalous
    Condition: Persistence omits the requested logical server
    Result: ServerNotFoundError is raised with the requested identifier
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    crud.get_server.return_value = None

    # Act
    with pytest.raises(ServerNotFoundError, match=f"server {SERVER_ID} not found"):
        await service.get(SERVER_ID)

    # Assert
    crud.get_server.assert_awaited_once_with(session, SERVER_ID)


@pytest.mark.parametrize(
    ("update_request", "expected_name"),
    [
        pytest.param(ServerUpdate(name="renamed-world"), "renamed-world", id="rename"),
        pytest.param(ServerUpdate(), "pumpkin-patch", id="no-op"),
    ],
)
async def test_server_service_update_006_nominal_metadata_update_is_committed(
    update_request: ServerUpdate,
    expected_name: str,
    crud: CrudMocks,
) -> None:
    """Test 006 - Nominal
    Condition: A partial metadata update changes the name or contains no fields
    Result: Editable metadata is persisted without changing deployment generation
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    persisted: Server = server()
    crud.get_server.return_value = persisted
    crud.update_server.return_value = persisted

    # Act
    result: Server = await service.update(SERVER_ID, update_request)

    # Assert
    assert result is persisted
    assert persisted.name == expected_name
    assert persisted.spec_generation == 1
    crud.update_server.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    ("persisted", "failure", "expected_error"),
    [
        pytest.param(None, None, ServerNotFoundError, id="missing"),
        pytest.param(
            server(),
            IntegrityError(
                "update server",
                {},
                RuntimeError("UNIQUE constraint failed: servers.name"),
            ),
            ServerNameConflictError,
            id="name-conflict",
        ),
        pytest.param(
            server(),
            IntegrityError("update server", {}, RuntimeError("constraint failed")),
            IntegrityError,
            id="other-integrity-failure",
        ),
        pytest.param(server(), RuntimeError("database unavailable"), RuntimeError, id="database"),
    ],
)
async def test_server_service_update_007_anomalous_failure_is_rolled_back(
    persisted: Server | None,
    failure: Exception | None,
    expected_error: type[Exception],
    crud: CrudMocks,
) -> None:
    """Test 007 - Anomalous
    Condition: The target is missing or persistence rejects the requested update
    Result: The transaction rolls back and exposes a stable or original failure
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    request: ServerUpdate = ServerUpdate(name="rename-target")
    crud.get_server.return_value = persisted
    crud.update_server.side_effect = failure

    # Act
    with pytest.raises(expected_error):
        await service.update(SERVER_ID, request)

    # Assert
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


async def test_server_service_delete_008_nominal_server_is_deleted(
    crud: CrudMocks,
) -> None:
    """Test 008 - Nominal
    Condition: Persistence contains the requested logical server
    Result: The server is deleted and the transaction is committed
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    persisted: Server = server()
    crud.get_server.return_value = persisted

    # Act
    await service.delete(SERVER_ID)

    # Assert
    crud.delete_server.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_server_service_delete_009_anomalous_server_is_missing(
    crud: CrudMocks,
) -> None:
    """Test 009 - Anomalous
    Condition: Persistence omits the requested logical server
    Result: ServerNotFoundError is raised and the transaction is rolled back
    """
    # Arrange
    service: ServerService
    session: AsyncMock
    service, session = service_dependencies()
    crud.get_server.return_value = None

    # Act
    with pytest.raises(ServerNotFoundError, match=f"server {SERVER_ID} not found"):
        await service.delete(SERVER_ID)

    # Assert
    crud.delete_server.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
