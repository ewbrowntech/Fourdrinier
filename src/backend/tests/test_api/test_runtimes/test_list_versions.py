"""
test_list_versions.py

Integration tests for listing Minecraft versions supported by a runtime.
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from fourdrinier.api.deps import get_runtime_registry
from fourdrinier.servers import PUMPKIN_MINECRAFT_VERSION
from fourdrinier.servers.runtimes import RuntimeRegistry


async def test_list_runtime_versions_001_nominal_pumpkin_returns_pinned_version(
    client: httpx.AsyncClient,
) -> None:
    """Test 001 - Nominal
    Condition: Versions are requested for the registered Pumpkin runtime
    Result: A one-element list containing the pinned Pumpkin Minecraft version
    """
    # Arrange / Act
    response: httpx.Response = await client.get("/api/v1/runtimes/pumpkin/versions")

    # Assert
    assert response.status_code == 200
    assert response.json() == [PUMPKIN_MINECRAFT_VERSION]


async def test_list_runtime_versions_002_anomalous_unknown_runtime_is_rejected(
    client: httpx.AsyncClient,
) -> None:
    """Test 002 - Anomalous
    Condition: Versions are requested for a runtime that is not a ServerRuntime value
    Result: HTTP 422 is returned
    """
    # Arrange / Act
    response: httpx.Response = await client.get("/api/v1/runtimes/paper/versions")

    # Assert
    assert response.status_code == 422


async def test_list_runtime_versions_003_anomalous_unregistered_runtime_is_not_found(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    """Test 003 - Anomalous
    Condition: The path runtime is valid but no adapter is registered for it
    Result: HTTP 404 with RuntimeNotRegisteredError detail is returned
    """
    # Arrange
    app.dependency_overrides[get_runtime_registry] = lambda: RuntimeRegistry()

    try:
        # Act
        response: httpx.Response = await client.get("/api/v1/runtimes/pumpkin/versions")

        # Assert
        assert response.status_code == 404
        assert response.json()["detail"] == (
            "no runtime adapter registered for runtime 'pumpkin'"
        )
    finally:
        app.dependency_overrides.pop(get_runtime_registry, None)
