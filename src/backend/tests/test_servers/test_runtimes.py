"""
test_runtimes.py

Unit tests for the provider-neutral runtime adapter registry.
"""

from __future__ import annotations

from fourdrinier.db.models import Server
from fourdrinier.servers.deployment import DeploymentSpec, ResourceAllocation
from fourdrinier.servers.runtimes import RuntimeAdapter, RuntimeRegistry
from fourdrinier.servers.types import ServerRuntime


class _StubRuntimeAdapter:
    runtime: ServerRuntime = ServerRuntime.PUMPKIN
    minecraft_version: str = "26.2"
    minimum_resources: ResourceAllocation = ResourceAllocation(
        cpu_millicores=2_000,
        memory_bytes=2_147_483_648,
    )

    def deployment_spec(self, server: Server) -> DeploymentSpec:
        """Fail if a registry test invokes runtime translation."""
        raise AssertionError("registry tests must not call the runtime adapter")


def test_runtime_registry_for_runtime_001_nominal_matching_adapter_is_returned() -> None:
    """Test 001 - Nominal
    Condition: A Pumpkin adapter declares the runtime required by the registry
    Result: The matching adapter is returned through the structural protocol
    """
    # Arrange
    pumpkin: _StubRuntimeAdapter = _StubRuntimeAdapter()
    registry: RuntimeRegistry = RuntimeRegistry(pumpkin)

    # Act
    adapter: RuntimeAdapter = registry.for_runtime(ServerRuntime.PUMPKIN)

    # Assert
    assert adapter is pumpkin
    assert adapter.runtime is ServerRuntime.PUMPKIN
    assert isinstance(adapter, RuntimeAdapter)
