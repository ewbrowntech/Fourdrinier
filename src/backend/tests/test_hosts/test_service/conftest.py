"""
conftest.py

Define shared fixtures for HostService unit tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from tests.test_hosts.test_service.support import CrudMocks


@pytest.fixture
def crud(monkeypatch: pytest.MonkeyPatch) -> CrudMocks:
    """Replace host CRUD operations with isolated async test doubles.

    Args:
        monkeypatch: Pytest fixture used to replace CRUD functions for one test.

    Returns:
        The CRUD test doubles installed for the current test.
    """
    create_host: AsyncMock = AsyncMock(spec=hosts_crud.create_host)
    delete_host: AsyncMock = AsyncMock(spec=hosts_crud.delete_host)
    get_host: AsyncMock = AsyncMock(spec=hosts_crud.get_host)
    get_keypair: AsyncMock = AsyncMock(spec=keypairs_crud.get_keypair)
    list_hosts: AsyncMock = AsyncMock(spec=hosts_crud.list_hosts)
    update_host: AsyncMock = AsyncMock(spec=hosts_crud.update_host)
    monkeypatch.setattr(hosts_crud, "create_host", create_host)
    monkeypatch.setattr(hosts_crud, "delete_host", delete_host)
    monkeypatch.setattr(hosts_crud, "get_host", get_host)
    monkeypatch.setattr(keypairs_crud, "get_keypair", get_keypair)
    monkeypatch.setattr(hosts_crud, "list_hosts", list_hosts)
    monkeypatch.setattr(hosts_crud, "update_host", update_host)
    get_keypair.return_value = object()
    return CrudMocks(
        create_host=create_host,
        delete_host=delete_host,
        get_host=get_host,
        get_keypair=get_keypair,
        list_hosts=list_hosts,
        update_host=update_host,
    )
