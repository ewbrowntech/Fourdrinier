"""
test_create.py

Unit tests for ServerService.create.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerCreate
from fourdrinier.servers import (
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
    ServerDesiredState,
    ServerNameConflictError,
    ServerResourceMinimumError,
    ServerRuntime,
    ServerVersionUnsupportedError,
)
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    CrudMocks,
    ServiceDependencies,
    server,
    service_dependencies,
)


@pytest.mark.parametrize(
    "requested_version",
    [
        pytest.param(None, id="default-version"),
        pytest.param("requested-version", id="explicit-version"),
    ],
)
async def test_server_service_create_001_nominal_fixed_configuration_is_committed(
    requested_version: str | None,
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A valid creation request omits or supplies a Minecraft version
    Result: A stopped generation-one configuration with the resolved version is committed
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    resolved_version: str = "runtime-resolved-version"
    dependencies.runtime.resolve_version.return_value = resolved_version
    request: ServerCreate = ServerCreate(
        name="lantern-grove",
        runtime=ServerRuntime.PUMPKIN,
        minecraft_version=requested_version,
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
    dependencies.runtime.resolve_version.assert_called_once_with(requested_version)
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
        runtime=ServerRuntime.PUMPKIN,
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


@pytest.mark.parametrize(
    ("create_request", "expected_message"),
    [
        pytest.param(
            ServerCreate(
                name="small-cpu",
                runtime=ServerRuntime.PUMPKIN,
                cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES - 1,
                memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
            ),
            "pumpkin requires at least 2000 CPU millicores",
            id="cpu",
        ),
        pytest.param(
            ServerCreate(
                name="small-memory",
                runtime=ServerRuntime.PUMPKIN,
                cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
                memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES - 1,
            ),
            "pumpkin requires at least 2147483648 memory bytes",
            id="memory",
        ),
    ],
)
async def test_server_service_create_003_anomalous_runtime_minimum_is_not_met(
    create_request: ServerCreate,
    expected_message: str,
    crud: CrudMocks,
) -> None:
    """Test 003 - Anomalous
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


async def test_server_service_create_004_anomalous_unsupported_version_is_rejected(
    crud: CrudMocks,
) -> None:
    """Test 004 - Anomalous
    Condition: The runtime adapter rejects the requested Minecraft version
    Result: ServerVersionUnsupportedError is raised without opening a write transaction
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    failure: ServerVersionUnsupportedError = ServerVersionUnsupportedError(
        "pumpkin only supports Minecraft version 26.2"
    )
    dependencies.runtime.resolve_version.side_effect = failure
    request: ServerCreate = ServerCreate(
        name="wrong-version",
        runtime=ServerRuntime.PUMPKIN,
        minecraft_version="1.8.8",
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
    )

    # Act
    with pytest.raises(ServerVersionUnsupportedError) as captured:
        await dependencies.service.create(request)

    # Assert
    assert captured.value is failure
    crud.create_server.assert_not_awaited()
    dependencies.session.commit.assert_not_awaited()
    dependencies.session.rollback.assert_not_awaited()
