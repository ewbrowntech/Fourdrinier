"""
test_update.py

Unit tests for ServerService.update.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerUpdate
from fourdrinier.servers import (
    PUMPKIN_MINECRAFT_VERSION,
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
    ServerNameConflictError,
    ServerNotFoundError,
    ServerResourceMinimumError,
    ServerVersionUnsupportedError,
)
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    SERVER_ID,
    CrudMocks,
    ServiceDependencies,
    server,
    service_dependencies,
)


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
async def test_server_service_update_001_nominal_metadata_update_is_committed(
    update_request: ServerUpdate,
    expected_name: str,
    expected_cpu_millicores: int,
    expected_memory_bytes: int,
    expected_generation: int,
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
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
async def test_server_service_update_002_anomalous_failure_is_rolled_back(
    persisted: Server | None,
    failure: Exception | None,
    expected_error: type[Exception],
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
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
async def test_server_service_update_003_anomalous_runtime_minimum_is_not_met(
    update_request: ServerUpdate,
    expected_message: str,
    crud: CrudMocks,
) -> None:
    """Test 003 - Anomalous
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


@pytest.mark.parametrize(
    ("update_request", "resolved_version", "expected_version", "expected_generation"),
    [
        pytest.param(
            ServerUpdate(minecraft_version="next-version"),
            "next-version",
            "next-version",
            2,
            id="version-changed",
        ),
        pytest.param(
            ServerUpdate(minecraft_version=PUMPKIN_MINECRAFT_VERSION),
            PUMPKIN_MINECRAFT_VERSION,
            PUMPKIN_MINECRAFT_VERSION,
            1,
            id="version-unchanged",
        ),
        pytest.param(
            ServerUpdate(minecraft_version="next-version", cpu_millicores=2_500),
            "next-version",
            "next-version",
            2,
            id="version-and-resources",
        ),
    ],
)
async def test_server_service_update_004_nominal_version_update_is_resolved(
    update_request: ServerUpdate,
    resolved_version: str,
    expected_version: str,
    expected_generation: int,
    crud: CrudMocks,
) -> None:
    """Test 004 - Nominal
    Condition: A partial update supplies a changed, unchanged, or combined Minecraft version
    Result: The resolved version persists and generation advances at most once
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    dependencies.runtime.resolve_version.return_value = resolved_version
    persisted: Server = server()
    crud.get_server.return_value = persisted
    crud.update_server.return_value = persisted

    # Act
    result: Server = await service.update(SERVER_ID, update_request)

    # Assert
    assert result is persisted
    assert persisted.minecraft_version == expected_version
    assert persisted.spec_generation == expected_generation
    dependencies.runtime.resolve_version.assert_called_once_with(update_request.minecraft_version)
    crud.update_server.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_server_service_update_005_anomalous_unsupported_version_is_rejected(
    crud: CrudMocks,
) -> None:
    """Test 005 - Anomalous
    Condition: The runtime adapter rejects the requested Minecraft version
    Result: ServerVersionUnsupportedError is raised and the persisted version is unchanged
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    failure: ServerVersionUnsupportedError = ServerVersionUnsupportedError(
        "pumpkin only supports Minecraft version 26.2"
    )
    dependencies.runtime.resolve_version.side_effect = failure
    persisted: Server = server()
    crud.get_server.return_value = persisted

    # Act
    with pytest.raises(ServerVersionUnsupportedError) as captured:
        await dependencies.service.update(SERVER_ID, ServerUpdate(minecraft_version="1.8.8"))

    # Assert
    assert captured.value is failure
    assert persisted.minecraft_version == PUMPKIN_MINECRAFT_VERSION
    assert persisted.spec_generation == 1
    crud.update_server.assert_not_awaited()
    dependencies.session.commit.assert_not_awaited()
    dependencies.session.rollback.assert_awaited_once_with()
