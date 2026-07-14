"""
drivers.py

Define the provider-neutral host driver contract and provider registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fourdrinier.hosts.errors import (
    HostDriverNotRegisteredError,
    HostProviderMismatchError,
)
from fourdrinier.hosts.types import HostPingResult, HostType

if TYPE_CHECKING:
    from fourdrinier.db.models import Host


@runtime_checkable
class HostDriver(Protocol):
    """Define remote operations shared by every host provider."""

    type: HostType

    async def ping(self, host: Host) -> HostPingResult:
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

        Raises:
            HostProviderMismatchError: If a driver declares the wrong provider type.
        """
        self._validate_driver(HostType.DOCKER, docker)
        self._validate_driver(HostType.KUBERNETES, kubernetes)
        self._drivers: dict[HostType, HostDriver] = {
            HostType.DOCKER: docker,
            HostType.KUBERNETES: kubernetes,
        }

    @staticmethod
    def _validate_driver(expected_type: HostType, driver: HostDriver) -> None:
        if driver.type is not expected_type:
            raise HostProviderMismatchError(
                f"expected a {expected_type.value} driver, got {driver.type.value}",
                provider=expected_type,
            )

    def for_host(self, host: Host) -> HostDriver:
        """Return the driver matching a host aggregate.

        Args:
            host: Host whose provider determines the selected driver.

        Returns:
            The registered driver for the host provider.

        Raises:
            HostDriverNotRegisteredError: If no driver supports the host provider.
        """
        try:
            driver: HostDriver = self._drivers[host.type]
        except KeyError as exc:
            raise HostDriverNotRegisteredError(
                f"no driver is registered for host provider {host.type!r}",
            ) from exc
        return driver


__all__: list[str] = ["HostDriver", "HostDriverRegistry"]
