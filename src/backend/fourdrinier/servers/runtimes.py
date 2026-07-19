"""
runtimes.py

Define the runtime adapter contract and select adapters by logical server runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fourdrinier.servers.deployment import ResourceAllocation
from fourdrinier.servers.types import ServerRuntime

if TYPE_CHECKING:
    from fourdrinier.db.models import Server
    from fourdrinier.servers.deployment import DeploymentSpec


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Translate logical servers into provider-neutral deployment specifications."""

    runtime: ServerRuntime
    minecraft_version: str
    minimum_resources: ResourceAllocation

    def deployment_spec(self, server: Server) -> DeploymentSpec:
        """Build the deployment specification for a logical server.

        Args:
            server: Logical server whose desired runtime configuration is translated.

        Returns:
            A provider-neutral container deployment specification.
        """
        ...


class RuntimeRegistry:
    """Select the adapter registered for a logical server runtime."""

    def __init__(self, pumpkin: RuntimeAdapter) -> None:
        """Register the adapters for all supported server runtimes.

        Args:
            pumpkin: Adapter whose declared runtime is Pumpkin.
        """
        self._adapters: dict[ServerRuntime, RuntimeAdapter] = {
            ServerRuntime.PUMPKIN: pumpkin,
        }

    def for_runtime(self, runtime: ServerRuntime) -> RuntimeAdapter:
        """Return the adapter matching a logical server runtime.

        Args:
            runtime: Runtime used to select an adapter.

        Returns:
            The registered adapter for the runtime.
        """
        adapter: RuntimeAdapter = self._adapters[runtime]
        return adapter


__all__: list[str] = ["RuntimeAdapter", "RuntimeRegistry"]
