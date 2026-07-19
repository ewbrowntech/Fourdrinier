"""
support.py

Provide shared test data and dependency doubles for ServerService unit tests.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server
from fourdrinier.servers import (
    PUMPKIN_MINECRAFT_VERSION,
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
    ServerDesiredState,
    ServerRuntime,
)
from fourdrinier.servers.deployment import ResourceAllocation
from fourdrinier.servers.runtimes import RuntimeAdapter, RuntimeRegistry
from fourdrinier.servers.service import ServerService

SERVER_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000201")


@dataclass(slots=True)
class CrudMocks:
    """Collect CRUD test doubles used by ServerService tests."""

    create_server: AsyncMock
    delete_server: AsyncMock
    get_server: AsyncMock
    list_servers: AsyncMock
    update_server: AsyncMock


@dataclass(slots=True)
class ServiceDependencies:
    """Collect the direct dependencies used by a ServerService unit test."""

    service: ServerService
    session: AsyncMock
    runtimes: Mock
    runtime: Mock


def service_dependencies() -> ServiceDependencies:
    """Build an isolated ServerService and its session dependency.

    Returns:
        The service and its request-scoped dependency test doubles.
    """
    session: AsyncMock = AsyncMock(spec=AsyncSession)
    runtimes: Mock = Mock(spec=RuntimeRegistry)
    runtime: Mock = Mock(spec=RuntimeAdapter)
    runtime.runtime = ServerRuntime.PUMPKIN
    runtime.minecraft_version = PUMPKIN_MINECRAFT_VERSION
    runtime.minimum_resources = ResourceAllocation(
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
    )
    runtimes.for_runtime.return_value = runtime
    service: ServerService = ServerService(
        session=cast(AsyncSession, session),
        runtimes=cast(RuntimeRegistry, runtimes),
    )
    dependencies: ServiceDependencies = ServiceDependencies(
        service=service,
        session=session,
        runtimes=runtimes,
        runtime=runtime,
    )
    return dependencies


def server(name: str = "pumpkin-patch") -> Server:
    """Build a logical server with stable test values.

    Args:
        name: Display name assigned to the logical server.

    Returns:
        A provider-independent logical server.
    """
    persisted: Server = Server(
        id=SERVER_ID,
        name=name,
        runtime=ServerRuntime.PUMPKIN,
        minecraft_version=PUMPKIN_MINECRAFT_VERSION,
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
        desired_state=ServerDesiredState.STOPPED,
        spec_generation=1,
    )
    return persisted
