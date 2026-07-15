"""
driver.py

Implement Docker operations behind the provider-neutral host driver boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fourdrinier.core.secrets import SecretDecryptor
from fourdrinier.hosts.docker import operations
from fourdrinier.hosts.docker.types import DockerHostPingResult
from fourdrinier.hosts.types import HostType

if TYPE_CHECKING:
    from fourdrinier.db.models import Host


class DockerHostDriver:
    """Perform Docker operations through SSH and the remote daemon API."""

    type: HostType = HostType.DOCKER

    def __init__(self, secret_decryptor: SecretDecryptor) -> None:
        """Initialize the driver with credential decryption.

        Args:
            secret_decryptor: Decryptor for stored SSH private keys.
        """
        self._secret_decryptor: SecretDecryptor = secret_decryptor

    async def ping(self, host: Host) -> DockerHostPingResult:
        """Check Docker daemon connectivity and SSH host-key trust."""
        return await operations.ping(host, self._secret_decryptor)


__all__: list[str] = ["DockerHostDriver"]
