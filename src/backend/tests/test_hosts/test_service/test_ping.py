"""
test_ping.py

Unit tests for HostService.ping.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import HostNotFoundError
from fourdrinier.hosts.drivers import HostDriver, HostDriverPingResult
from fourdrinier.hosts.service import HostService
from tests.test_hosts.test_service.support import (
    HOST_ID,
    OBSERVED_AT,
    CrudMocks,
    host,
    ping_result,
    service_dependencies,
)


async def test_host_service_ping_001_nominal_observation_is_committed(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A matching provider driver successfully checks the requested host
    Result: The observation time is persisted and the provider-neutral result is returned
    """
    # Arrange
    service: HostService
    session: AsyncMock
    drivers: Mock
    _secret_encryptor: Mock
    service, session, drivers, _secret_encryptor = service_dependencies()
    persisted: Host = host()
    driver: AsyncMock = AsyncMock(spec=HostDriver)
    expected: HostDriverPingResult = ping_result()
    crud.get_host.return_value = persisted
    drivers.for_host.return_value = driver
    driver.ping.return_value = expected

    # Act
    result: HostDriverPingResult = await service.ping(HOST_ID)

    # Assert
    assert result is expected
    assert persisted.last_seen_at is OBSERVED_AT
    drivers.for_host.assert_called_once_with(persisted)
    driver.ping.assert_awaited_once_with(persisted)
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


async def test_host_service_ping_002_anomalous_missing_host_is_rolled_back(
    crud: CrudMocks,
) -> None:
    """Test 002 - Anomalous
    Condition: No host exists for the requested ping target
    Result: HostNotFoundError is raised without selecting a driver and the transaction rolls back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    drivers: Mock
    _secret_encryptor: Mock
    service, session, drivers, _secret_encryptor = service_dependencies()
    crud.get_host.return_value = None

    # Act
    with pytest.raises(HostNotFoundError, match=f"host {HOST_ID} not found"):
        await service.ping(HOST_ID)

    # Assert
    drivers.for_host.assert_not_called()
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize(
    "failure_source",
    [
        pytest.param("driver", id="driver-failure"),
        pytest.param("commit", id="commit-failure"),
    ],
)
async def test_host_service_ping_003_anomalous_operation_failure_is_rolled_back(
    failure_source: str,
    crud: CrudMocks,
) -> None:
    """Test 003 - Anomalous
    Condition: The provider check or the local commit fails
    Result: The original failure propagates after the transaction is rolled back
    """
    # Arrange
    service: HostService
    session: AsyncMock
    drivers: Mock
    _secret_encryptor: Mock
    service, session, drivers, _secret_encryptor = service_dependencies()
    persisted: Host = host()
    driver: AsyncMock = AsyncMock(spec=HostDriver)
    failure: RuntimeError = RuntimeError(f"{failure_source} failed")
    expected: HostDriverPingResult = ping_result()
    crud.get_host.return_value = persisted
    drivers.for_host.return_value = driver
    driver.ping.return_value = expected
    if failure_source == "driver":
        driver.ping.side_effect = failure
    else:
        session.commit.side_effect = failure

    # Act
    with pytest.raises(RuntimeError, match=f"{failure_source} failed") as captured:
        await service.ping(HOST_ID)

    # Assert
    assert captured.value is failure
    session.rollback.assert_awaited_once_with()
