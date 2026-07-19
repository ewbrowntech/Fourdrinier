"""
test_delete.py

Unit tests for ServerService.delete.
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


async def test_server_service_delete_001_nominal_server_is_deleted(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
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


async def test_server_service_delete_002_anomalous_server_is_missing(
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
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
