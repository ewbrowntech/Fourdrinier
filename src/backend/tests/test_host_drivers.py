"""
test_host_drivers.py

Unit tests for the provider-neutral host driver boundary and registry.
"""

from __future__ import annotations

from typing import cast

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import (
    HostDriverNotRegisteredError,
    HostDriverUnavailableError,
    HostPingResult,
    HostProviderMismatchError,
    HostType,
)
from fourdrinier.hosts.docker import DockerHostDriver
from fourdrinier.hosts.drivers import HostDriver, HostDriverRegistry
from fourdrinier.hosts.kubernetes import KubernetesHostDriver


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


@pytest.mark.parametrize(
    ("driver", "host_type", "message"),
    [
        pytest.param(
            DockerHostDriver(),
            HostType.DOCKER,
            "Docker host ping is not implemented",
            id="docker",
        ),
        pytest.param(
            KubernetesHostDriver(),
            HostType.KUBERNETES,
            "Kubernetes host ping is not implemented",
            id="kubernetes",
        ),
    ],
)
async def test_host_driver_ping_004_anomalous_placeholder_is_unavailable(
    driver: HostDriver,
    host_type: HostType,
    message: str,
) -> None:
    """Test 004 - Anomalous
    Condition: A matching host is passed to a placeholder provider driver
    Result: HostDriverUnavailableError reports that ping is not implemented
    """
    # Arrange
    host: Host = Host(type=host_type, name="production")

    # Act
    with pytest.raises(HostDriverUnavailableError, match=message) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is host_type


@pytest.mark.parametrize(
    ("driver", "host_type", "driver_name"),
    [
        pytest.param(
            DockerHostDriver(),
            HostType.KUBERNETES,
            "Docker",
            id="docker-with-kubernetes-host",
        ),
        pytest.param(
            KubernetesHostDriver(),
            HostType.DOCKER,
            "Kubernetes",
            id="kubernetes-with-docker-host",
        ),
    ],
)
async def test_host_driver_ping_005_anomalous_host_type_does_not_match_driver(
    driver: HostDriver,
    host_type: HostType,
    driver_name: str,
) -> None:
    """Test 005 - Anomalous
    Condition: A provider driver receives a host belonging to the other provider
    Result: HostProviderMismatchError is raised before any remote operation
    """
    # Arrange
    host: Host = Host(type=host_type, name="production")

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match=f"the {driver_name} driver cannot operate on a {host_type.value} host",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is driver.type
