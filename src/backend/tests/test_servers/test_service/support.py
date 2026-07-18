"""
support.py

Provide shared test data and dependency doubles for ServerService unit tests.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import cast
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server
from fourdrinier.servers import (
    PUMPKIN_MINECRAFT_VERSION,
    ServerDesiredState,
    ServerRuntime,
)
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


def service_dependencies() -> tuple[ServerService, AsyncMock]:
    """Build an isolated ServerService and its session dependency.

    Returns:
        The service and request-scoped session test double.
    """
    session: AsyncMock = AsyncMock(spec=AsyncSession)
    service: ServerService = ServerService(session=cast(AsyncSession, session))
    return service, session


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
        desired_state=ServerDesiredState.STOPPED,
        spec_generation=1,
    )
    return persisted
