"""
test_registry.py

Unit tests for the provider-neutral host driver registry.
"""

from __future__ import annotations

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import HostType
from fourdrinier.hosts.drivers import HostDriver, HostDriverPingResult, HostDriverRegistry


class _StubHostDriver:
    def __init__(self, host_type: HostType) -> None:
        self.type: HostType = host_type

    async def ping(self, host: Host) -> HostDriverPingResult:
        """Fail if a registry test invokes a provider operation."""
        raise AssertionError("registry tests must not call the provider driver")


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
def test_host_driver_registry_for_host_001_nominal_matching_driver_is_returned(
    host_type: HostType,
) -> None:
    """Test 001 - Nominal
    Condition: Drivers declare the provider types required by the registry
    Result: The driver matching the host type is returned through the protocol
    """
    # Arrange
    docker: _StubHostDriver = _StubHostDriver(HostType.DOCKER)
    kubernetes: _StubHostDriver = _StubHostDriver(HostType.KUBERNETES)
    registry: HostDriverRegistry = HostDriverRegistry(docker, kubernetes)
    host: Host = Host(type=host_type, name="production")
    expected_driver: _StubHostDriver = docker if host_type is HostType.DOCKER else kubernetes

    # Act
    driver: HostDriver = registry.for_host(host)

    # Assert
    assert driver is expected_driver
    assert isinstance(driver, HostDriver)
    assert driver.type is host_type
