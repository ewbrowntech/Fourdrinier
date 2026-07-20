"""
test_runtimes.py

Unit tests for the provider-neutral runtime adapter registry.
"""

from __future__ import annotations

import pytest

from fourdrinier.db.models import Server
from fourdrinier.servers.deployment import DeploymentSpec, ResourceAllocation
from fourdrinier.servers.errors import RuntimeNotRegisteredError
from fourdrinier.servers.runtimes import RuntimeAdapter, RuntimeRegistry
from fourdrinier.servers.types import ServerRuntime


class _StubRuntimeAdapter:
    runtime: ServerRuntime = ServerRuntime.PUMPKIN
    minimum_resources: ResourceAllocation = ResourceAllocation(
        cpu_millicores=2_000,
        memory_bytes=2_147_483_648,
    )

    async def resolve_version(self, requested: str | None) -> str:
        """Fail if a registry test invokes version resolution."""
        raise AssertionError("registry tests must not call the runtime adapter")

    async def list_versions(self) -> list[str]:
        """Fail if a registry test invokes version discovery."""
        raise AssertionError("registry tests must not call the runtime adapter")

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


def test_runtime_registry_for_runtime_002_anomalous_runtime_has_no_adapter() -> None:
    """Test 002 - Anomalous
    Condition: No adapter declaring the requested runtime was registered
    Result: RuntimeNotRegisteredError("no runtime adapter registered for runtime 'pumpkin'")
    """
    # Arrange
    registry: RuntimeRegistry = RuntimeRegistry()

    # Act / Assert
    with pytest.raises(
        RuntimeNotRegisteredError,
        match="no runtime adapter registered for runtime 'pumpkin'",
    ):
        registry.for_runtime(ServerRuntime.PUMPKIN)
