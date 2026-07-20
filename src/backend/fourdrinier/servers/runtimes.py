"""
runtimes.py

Define the runtime adapter contract and select adapters by logical server runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from fourdrinier.servers.deployment import ResourceAllocation
from fourdrinier.servers.errors import RuntimeNotRegisteredError
from fourdrinier.servers.types import ServerRuntime

if TYPE_CHECKING:
    from fourdrinier.db.models import Server
    from fourdrinier.servers.deployment import DeploymentSpec


@runtime_checkable
class RuntimeAdapter(Protocol):
    """Translate logical servers into provider-neutral deployment specifications."""

    runtime: ServerRuntime
    minimum_resources: ResourceAllocation

    async def resolve_version(self, requested: str | None) -> str:
        """Resolve a requested Minecraft version to one this runtime supports.

        Args:
            requested: Minecraft version requested by the caller, or None for the
                runtime's default version.

        Returns:
            The concrete Minecraft version the runtime will deploy.

        Raises:
            ServerVersionUnsupportedError: If the runtime does not support the
                requested version.
            RuntimeVersionSourceError: If the runtime's version source cannot be
                consulted.
        """
        ...

    async def list_versions(self) -> list[str]:
        """List Minecraft versions this runtime can deploy.

        Returns:
            Minecraft versions accepted by the runtime, newest or preferred first
            when the runtime defines an order.
        """
        ...

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

    def __init__(self, *adapters: RuntimeAdapter) -> None:
        """Register adapters keyed by each adapter's declared runtime.

        Args:
            adapters: Adapters for every supported server runtime.
        """
        self._adapters: dict[ServerRuntime, RuntimeAdapter] = {
            adapter.runtime: adapter for adapter in adapters
        }

    def for_runtime(self, runtime: ServerRuntime) -> RuntimeAdapter:
        """Return the adapter matching a logical server runtime.

        Args:
            runtime: Runtime used to select an adapter.

        Returns:
            The registered adapter for the runtime.

        Raises:
            RuntimeNotRegisteredError: If no adapter declares the requested runtime.
        """
        adapter: RuntimeAdapter | None = self._adapters.get(runtime)
        if adapter is None:
            raise RuntimeNotRegisteredError(
                f"no runtime adapter registered for runtime {runtime.value!r}"
            )
        return adapter


__all__: list[str] = ["RuntimeAdapter", "RuntimeRegistry"]
