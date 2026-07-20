"""
test_list.py

Unit tests for ServerService.list.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from fourdrinier.db.models import Server
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    CrudMocks,
    ServiceDependencies,
    server,
    service_dependencies,
)


async def test_server_service_list_001_nominal_ordered_servers_are_forwarded(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
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
