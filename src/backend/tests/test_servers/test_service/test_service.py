"""
test_service.py

Unit tests for logical server persistence orchestration.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerCreate, ServerUpdate
from fourdrinier.servers import (
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
    ServerDesiredState,
    ServerNameConflictError,
    ServerNotFoundError,
    ServerResourceMinimumError,
    ServerRuntime,
)
from fourdrinier.servers.deployment import DeploymentSpec
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    SERVER_ID,
    CrudMocks,
    ServiceDependencies,
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    resolved_version: str = "runtime-resolved-version"
    dependencies.runtime.minecraft_version = resolved_version
    request: ServerCreate = ServerCreate(
        name="lantern-grove",
        cpu_millicores=2_500,
        memory_bytes=3_221_225_472,
    )
    created: Server = server(request.name)
    crud.create_server.return_value = created

    # Act
    result: Server = await service.create(request)

    # Assert
    persisted: Server = crud.create_server.await_args.args[1]
    assert result is created
    assert persisted.name == request.name
    assert persisted.runtime is ServerRuntime.PUMPKIN
    assert persisted.minecraft_version == resolved_version
    assert persisted.cpu_millicores == request.cpu_millicores
    assert persisted.memory_bytes == request.memory_bytes
    assert persisted.desired_state is ServerDesiredState.STOPPED
    assert persisted.spec_generation == 1
    dependencies.runtimes.for_runtime.assert_called_once_with(ServerRuntime.PUMPKIN)
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    request: ServerCreate = ServerCreate(
        name="conflicted-world",
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
    )
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    crud.get_server.return_value = None

    # Act
    with pytest.raises(ServerNotFoundError, match=f"server {SERVER_ID} not found"):
        await service.get(SERVER_ID)

    # Assert
    crud.get_server.assert_awaited_once_with(session, SERVER_ID)


async def test_server_service_deployment_spec_010_nominal_runtime_translates_server(
    crud: CrudMocks,
) -> None:
    """Test 010 - Nominal
    Condition: A saved server has a registered runtime adapter
    Result: The service returns the adapter's provider-neutral deployment specification
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    persisted: Server = server()
    specification: DeploymentSpec = cast(DeploymentSpec, Mock(spec=DeploymentSpec))
    crud.get_server.return_value = persisted
    dependencies.runtime.deployment_spec.return_value = specification

    # Act
    result: DeploymentSpec = await service.deployment_spec(SERVER_ID)

    # Assert
    assert result is specification
    crud.get_server.assert_awaited_once_with(session, SERVER_ID)
    dependencies.runtimes.for_runtime.assert_called_once_with(ServerRuntime.PUMPKIN)
    dependencies.runtime.deployment_spec.assert_called_once_with(persisted)


@pytest.mark.parametrize(
    ("create_request", "expected_message"),
    [
        pytest.param(
            ServerCreate(
                name="small-cpu",
                cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES - 1,
                memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
            ),
            "pumpkin requires at least 2000 CPU millicores",
            id="cpu",
        ),
        pytest.param(
            ServerCreate(
                name="small-memory",
                cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
                memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES - 1,
            ),
            "pumpkin requires at least 2147483648 memory bytes",
            id="memory",
        ),
    ],
)
async def test_server_service_create_011_anomalous_runtime_minimum_is_not_met(
    create_request: ServerCreate,
    expected_message: str,
    crud: CrudMocks,
) -> None:
    """Test 011 - Anomalous
    Condition: A creation request is below the selected runtime's CPU or memory minimum
    Result: ServerResourceMinimumError is raised without opening a write transaction
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()

    # Act
    with pytest.raises(ServerResourceMinimumError, match=expected_message):
        await dependencies.service.create(create_request)

    # Assert
    crud.create_server.assert_not_awaited()
    dependencies.session.commit.assert_not_awaited()
    dependencies.session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    (
        "update_request",
        "expected_name",
        "expected_cpu_millicores",
        "expected_memory_bytes",
        "expected_generation",
    ),
    [
        pytest.param(
            ServerUpdate(name="renamed-world"),
            "renamed-world",
            2_000,
            2_147_483_648,
            1,
            id="rename",
        ),
        pytest.param(
            ServerUpdate(),
            "pumpkin-patch",
            2_000,
            2_147_483_648,
            1,
            id="no-op",
        ),
        pytest.param(
            ServerUpdate(cpu_millicores=2_500),
            "pumpkin-patch",
            2_500,
            2_147_483_648,
            2,
            id="cpu",
        ),
        pytest.param(
            ServerUpdate(memory_bytes=3_221_225_472),
            "pumpkin-patch",
            2_000,
            3_221_225_472,
            2,
            id="memory",
        ),
        pytest.param(
            ServerUpdate(cpu_millicores=2_500, memory_bytes=3_221_225_472),
            "pumpkin-patch",
            2_500,
            3_221_225_472,
            2,
            id="cpu-and-memory",
        ),
        pytest.param(
            ServerUpdate(cpu_millicores=2_000, memory_bytes=2_147_483_648),
            "pumpkin-patch",
            2_000,
            2_147_483_648,
            1,
            id="unchanged-resources",
        ),
    ],
)
async def test_server_service_update_006_nominal_metadata_update_is_committed(
    update_request: ServerUpdate,
    expected_name: str,
    expected_cpu_millicores: int,
    expected_memory_bytes: int,
    expected_generation: int,
    crud: CrudMocks,
) -> None:
    """Test 006 - Nominal
    Condition: A partial update changes metadata, resources, both resources, or nothing
    Result: Resource changes increment generation once while metadata and no-ops do not
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    persisted: Server = server()
    crud.get_server.return_value = persisted
    crud.update_server.return_value = persisted

    # Act
    result: Server = await service.update(SERVER_ID, update_request)

    # Assert
    assert result is persisted
    assert persisted.name == expected_name
    assert persisted.cpu_millicores == expected_cpu_millicores
    assert persisted.memory_bytes == expected_memory_bytes
    assert persisted.spec_generation == expected_generation
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    request: ServerUpdate = ServerUpdate(name="rename-target")
    crud.get_server.return_value = persisted
    crud.update_server.side_effect = failure

    # Act
    with pytest.raises(expected_error):
        await service.update(SERVER_ID, request)

    # Assert
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    ("update_request", "expected_message"),
    [
        pytest.param(
            ServerUpdate(cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES - 1),
            "pumpkin requires at least 2000 CPU millicores",
            id="cpu",
        ),
        pytest.param(
            ServerUpdate(memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES - 1),
            "pumpkin requires at least 2147483648 memory bytes",
            id="memory",
        ),
    ],
)
async def test_server_service_update_012_anomalous_runtime_minimum_is_not_met(
    update_request: ServerUpdate,
    expected_message: str,
    crud: CrudMocks,
) -> None:
    """Test 012 - Anomalous
    Condition: A resource update would put the server below its runtime minimum
    Result: ServerResourceMinimumError is raised and the persisted allocation is unchanged
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    persisted: Server = server()
    crud.get_server.return_value = persisted

    # Act
    with pytest.raises(ServerResourceMinimumError, match=expected_message):
        await dependencies.service.update(SERVER_ID, update_request)

    # Assert
    assert persisted.cpu_millicores == PUMPKIN_MINIMUM_CPU_MILLICORES
    assert persisted.memory_bytes == PUMPKIN_MINIMUM_MEMORY_BYTES
    assert persisted.spec_generation == 1
    crud.update_server.assert_not_awaited()
    dependencies.session.commit.assert_not_awaited()
    dependencies.session.rollback.assert_awaited_once_with()


async def test_server_service_delete_008_nominal_server_is_deleted(
    crud: CrudMocks,
) -> None:
    """Test 008 - Nominal
    Condition: Persistence contains the requested logical server
    Result: The server is deleted and the transaction is committed
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
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
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    crud.get_server.return_value = None

    # Act
    with pytest.raises(ServerNotFoundError, match=f"server {SERVER_ID} not found"):
        await service.delete(SERVER_ID)

    # Assert
    crud.delete_server.assert_not_awaited()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
