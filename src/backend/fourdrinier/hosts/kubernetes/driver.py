"""
driver.py

Implement Kubernetes operations behind the provider-neutral host driver boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fourdrinier.core.secrets import SecretDecryptor
from fourdrinier.hosts.kubernetes.operations.ping import ping
from fourdrinier.hosts.kubernetes.types import KubernetesHostPingResult
from fourdrinier.hosts.types import HostType

if TYPE_CHECKING:
    from fourdrinier.db.models import Host


class KubernetesHostDriver:
    """Perform Kubernetes operations through the cluster API."""

    type: HostType = HostType.KUBERNETES

    def __init__(self, secret_decryptor: SecretDecryptor) -> None:
        """Initialize the driver with credential decryption.

        Args:
            secret_decryptor: Decryptor for the stored Kubernetes bearer token.
        """
        self._secret_decryptor: SecretDecryptor = secret_decryptor

    async def ping(self, host: Host) -> KubernetesHostPingResult:
        """Check cluster connectivity, identity, and deployment permissions."""
        return await ping(host, self._secret_decryptor)


__all__: list[str] = ["KubernetesHostDriver"]
