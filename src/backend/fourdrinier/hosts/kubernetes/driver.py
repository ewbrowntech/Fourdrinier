"""
driver.py

Provide the Kubernetes host driver boundary while remote ping wiring is pending.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fourdrinier.hosts.errors import (
    HostDriverUnavailableError,
    HostProviderMismatchError,
)
from fourdrinier.hosts.types import HostPingResult, HostType

if TYPE_CHECKING:
    from fourdrinier.db.models import Host


class KubernetesHostDriver:
    """Represent Kubernetes operations behind the provider-neutral driver contract."""

    type: HostType = HostType.KUBERNETES

    async def ping(self, host: Host) -> HostPingResult:
        """Reject Kubernetes ping requests until the provider is wired end to end.

        Args:
            host: Host aggregate with Kubernetes details loaded.

        Returns:
            Provider-neutral observations when Kubernetes ping is implemented.

        Raises:
            HostProviderMismatchError: If the host is not a Kubernetes host.
            HostDriverUnavailableError: Because Kubernetes ping is not implemented yet.
        """
        if host.type is not self.type:
            raise HostProviderMismatchError(
                f"the Kubernetes driver cannot operate on a {host.type.value} host",
                provider=self.type,
            )
        raise HostDriverUnavailableError(
            "Kubernetes host ping is not implemented",
            provider=self.type,
        )


__all__: list[str] = ["KubernetesHostDriver"]
