"""
test_delete.py

Unit tests for HostService.delete.
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


async def test_host_service_delete_001_nominal_host_is_deleted_and_committed(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: The requested host exists
    Result: Its aggregate is deleted and the transaction is committed
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
    result: None = await service.delete(HOST_ID)

    # Assert
    assert result is None
    crud.delete_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.parametrize(
    ("persisted", "failure", "message"),
    [
        pytest.param(None, None, f"host {HOST_ID} not found", id="missing-host"),
        pytest.param(host(), RuntimeError("delete failed"), "delete failed", id="delete-failure"),
    ],
)
async def test_host_service_delete_002_anomalous_failure_is_rolled_back(
    persisted: Host | None,
    failure: RuntimeError | None,
    message: str,
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
    Condition: The host is missing or its persistence deletion fails
    Result: The write transaction rolls back and the typed or original failure propagates
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    crud.get_host.return_value = persisted
    crud.delete_host.side_effect = failure
    expected_error: type[Exception] = HostNotFoundError if persisted is None else RuntimeError

    # Act
    with pytest.raises(expected_error, match=message):
        await service.delete(HOST_ID)

    # Assert
    if persisted is None:
        crud.delete_host.assert_not_awaited()
    else:
        crud.delete_host.assert_awaited_once_with(session, persisted)
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()
