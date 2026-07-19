"""
test_get.py

Unit tests for HostService.get.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import HostNotFoundError
from fourdrinier.hosts.service import HostService
from tests.test_hosts.test_service.support import (
    HOST_ID,
    CrudMocks,
    host,
    service_dependencies,
)


async def test_host_service_get_001_nominal_host_is_returned(crud: CrudMocks) -> None:
    """Test 001 - Nominal
    Condition: Host persistence contains a host for the requested ID
    Result: The matching aggregate is returned without ending the read transaction
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    persisted: Host = host()
    crud.get_host.return_value = persisted

    # Act
    result: Host = await service.get(HOST_ID)

    # Assert
    assert result is persisted
    crud.get_host.assert_awaited_once_with(session, HOST_ID)
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


async def test_host_service_get_002_anomalous_unknown_host_is_rejected(
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
    Condition: Host persistence does not contain the requested host ID
    Result: HostNotFoundError identifies the missing host
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    crud.get_host.return_value = None

    # Act
    with pytest.raises(HostNotFoundError, match=f"host {HOST_ID} not found"):
        await service.get(HOST_ID)

    # Assert
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()
