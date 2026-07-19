"""
conftest.py

Define shared fixtures for ServerService unit tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from fourdrinier.db.crud import servers as servers_crud
from tests.test_servers.test_service.support import CrudMocks


@pytest.fixture
def crud(monkeypatch: pytest.MonkeyPatch) -> CrudMocks:
    """Replace logical server CRUD operations with isolated test doubles.

    Args:
        monkeypatch: Pytest fixture used to replace CRUD functions for one test.

    Returns:
        The CRUD test doubles installed for the current test.
    """
    create_server: AsyncMock = AsyncMock(spec=servers_crud.create_server)
    delete_server: AsyncMock = AsyncMock(spec=servers_crud.delete_server)
    get_server: AsyncMock = AsyncMock(spec=servers_crud.get_server)
    list_servers: AsyncMock = AsyncMock(spec=servers_crud.list_servers)
    update_server: AsyncMock = AsyncMock(spec=servers_crud.update_server)
    monkeypatch.setattr(servers_crud, "create_server", create_server)
    monkeypatch.setattr(servers_crud, "delete_server", delete_server)
    monkeypatch.setattr(servers_crud, "get_server", get_server)
    monkeypatch.setattr(servers_crud, "list_servers", list_servers)
    monkeypatch.setattr(servers_crud, "update_server", update_server)
    return CrudMocks(
        create_server=create_server,
        delete_server=delete_server,
        get_server=get_server,
        list_servers=list_servers,
        update_server=update_server,
    )
