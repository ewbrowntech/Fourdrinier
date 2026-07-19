"""
drivers.py

Define the provider-neutral host driver contract and provider registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fourdrinier.hosts.docker.types import DockerHostPingResult
from fourdrinier.hosts.kubernetes.types import KubernetesHostPingResult
from fourdrinier.hosts.types import HostType

if TYPE_CHECKING:
    from fourdrinier.db.models import Host

type HostDriverPingResult = DockerHostPingResult | KubernetesHostPingResult


@runtime_checkable
class HostDriver(Protocol):
    """Define remote operations shared by every host provider."""

    type: HostType

    async def ping(self, host: Host) -> HostDriverPingResult:
        """Check connectivity to a registered host.

        Args:
            host: Host aggregate with provider details loaded.

        Returns:
            Provider-neutral observations from a successful connectivity check.

        Raises:
            HostError: If the host cannot be checked successfully.
        """
        ...


class HostDriverRegistry:
    """Select a host driver by the provider declared on a host aggregate."""

    def __init__(self, docker: HostDriver, kubernetes: HostDriver) -> None:
        """Register the drivers for all supported host providers.

        Args:
            docker: Driver whose declared provider is Docker.
            kubernetes: Driver whose declared provider is Kubernetes.
        """
        self._drivers: dict[HostType, HostDriver] = {
            HostType.DOCKER: docker,
            HostType.KUBERNETES: kubernetes,
        }

    def for_host(self, host: Host) -> HostDriver:
        """Return the driver matching a host aggregate.

        Args:
            host: Host whose provider determines the selected driver.

        Returns:
            The registered driver for the host provider.
        """
        driver: HostDriver = self._drivers[host.type]
        return driver


__all__: list[str] = ["HostDriver", "HostDriverPingResult", "HostDriverRegistry"]
