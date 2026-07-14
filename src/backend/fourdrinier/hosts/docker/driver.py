"""
driver.py

Provide the Docker host driver boundary while remote ping wiring is pending.
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


class DockerHostDriver:
    """Represent Docker operations behind the provider-neutral driver contract."""

    type: HostType = HostType.DOCKER

    async def ping(self, host: Host) -> HostPingResult:
        """Reject Docker ping requests until the provider is wired end to end.

        Args:
            host: Host aggregate with Docker details loaded.

        Returns:
            Provider-neutral observations when Docker ping is implemented.

        Raises:
            HostProviderMismatchError: If the host is not a Docker host.
            HostDriverUnavailableError: Because Docker ping is not implemented yet.
        """
        if host.type is not self.type:
            raise HostProviderMismatchError(
                f"the Docker driver cannot operate on a {host.type.value} host",
                provider=self.type,
            )
        raise HostDriverUnavailableError(
            "Docker host ping is not implemented",
            provider=self.type,
        )


__all__: list[str] = ["DockerHostDriver"]
