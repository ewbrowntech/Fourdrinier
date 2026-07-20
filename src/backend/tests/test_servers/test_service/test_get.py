"""
test_get.py

Unit tests for ServerService.get.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from fourdrinier.db.models import Server
from fourdrinier.servers import ServerNotFoundError
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    SERVER_ID,
    CrudMocks,
    ServiceDependencies,
    server,
    service_dependencies,
)


async def test_server_service_get_001_nominal_server_is_returned(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
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


async def test_server_service_get_002_anomalous_server_is_missing(
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
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
