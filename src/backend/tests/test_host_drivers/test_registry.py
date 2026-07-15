"""
test_registry.py

Unit tests for the provider-neutral host driver registry.
"""

from __future__ import annotations

from typing import cast

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import (
    HostDriverNotRegisteredError,
    HostPingResult,
    HostProviderMismatchError,
    HostType,
)
from fourdrinier.hosts.drivers import HostDriver, HostDriverRegistry


class _StubHostDriver:
    def __init__(self, host_type: HostType) -> None:
        self.type: HostType = host_type

    async def ping(self, host: Host) -> HostPingResult:
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


def test_host_driver_registry_init_002_anomalous_driver_declares_wrong_type() -> None:
    """Test 002 - Anomalous
    Condition: The driver supplied for Docker declares itself as Kubernetes
    Result: HostProviderMismatchError identifies the expected provider
    """
    # Arrange
    docker: _StubHostDriver = _StubHostDriver(HostType.KUBERNETES)
    kubernetes: _StubHostDriver = _StubHostDriver(HostType.KUBERNETES)

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="expected a docker driver, got kubernetes",
    ) as captured:
        HostDriverRegistry(docker, kubernetes)

    # Assert
    assert captured.value.provider is HostType.DOCKER


def test_host_driver_registry_for_host_003_anomalous_provider_is_not_registered() -> None:
    """Test 003 - Anomalous
    Condition: A malformed host contains a provider outside the supported enum
    Result: HostDriverNotRegisteredError is raised instead of leaking KeyError
    """
    # Arrange
    registry: HostDriverRegistry = HostDriverRegistry(
        _StubHostDriver(HostType.DOCKER),
        _StubHostDriver(HostType.KUBERNETES),
    )
    host: Host = Host(type=HostType.DOCKER, name="production")
    host.type = cast(HostType, "unsupported")

    # Act
    with pytest.raises(
        HostDriverNotRegisteredError,
        match="no driver is registered for host provider 'unsupported'",
    ) as captured:
        registry.for_host(host)

    # Assert
    assert isinstance(captured.value.__cause__, KeyError)
