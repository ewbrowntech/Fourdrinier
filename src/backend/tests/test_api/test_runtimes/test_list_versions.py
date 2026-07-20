"""
test_list_versions.py

Integration tests for listing Minecraft versions supported by a runtime.
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from fourdrinier.api.deps import get_runtime_registry
from fourdrinier.servers import PUMPKIN_MINECRAFT_VERSION
from fourdrinier.servers.paper import PaperRuntime
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


async def test_list_runtime_versions_002_nominal_paper_returns_fill_versions(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    """Test 002 - Nominal
    Condition: Versions are requested for the Paper runtime and the Fill API responds
    Result: The flattened Fill versions are returned newest first
    """
    # Arrange
    payload: dict[str, dict[str, list[str]]] = {
        "versions": {"26.2": ["26.2"], "1.21": ["1.21.4", "1.21.3"]},
    }
    transport: httpx.MockTransport = httpx.MockTransport(
        lambda request: httpx.Response(200, json=payload)
    )
    app.dependency_overrides[get_runtime_registry] = lambda: RuntimeRegistry(
        PaperRuntime(transport=transport)
    )

    try:
        # Act
        response: httpx.Response = await client.get("/api/v1/runtimes/paper/versions")

        # Assert
        assert response.status_code == 200
        assert response.json() == ["26.2", "1.21.4", "1.21.3"]
    finally:
        app.dependency_overrides.pop(get_runtime_registry, None)


async def test_list_runtime_versions_003_anomalous_unknown_runtime_is_rejected(
    client: httpx.AsyncClient,
) -> None:
    """Test 003 - Anomalous
    Condition: Versions are requested for a runtime that is not a ServerRuntime value
    Result: HTTP 422 is returned
    """
    # Arrange / Act
    response: httpx.Response = await client.get("/api/v1/runtimes/forge/versions")

    # Assert
    assert response.status_code == 422


async def test_list_runtime_versions_004_anomalous_unregistered_runtime_is_not_found(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    """Test 004 - Anomalous
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
        assert response.json()["detail"] == ("no runtime adapter registered for runtime 'pumpkin'")
    finally:
        app.dependency_overrides.pop(get_runtime_registry, None)


async def test_list_runtime_versions_005_anomalous_version_source_failure_is_bad_gateway(
    app: FastAPI,
    client: httpx.AsyncClient,
) -> None:
    """Test 005 - Anomalous
    Condition: The Paper runtime's Fill API request fails with a server error
    Result: HTTP 502 with RuntimeVersionSourceError detail is returned
    """
    # Arrange
    transport: httpx.MockTransport = httpx.MockTransport(lambda request: httpx.Response(503))
    app.dependency_overrides[get_runtime_registry] = lambda: RuntimeRegistry(
        PaperRuntime(transport=transport)
    )

    try:
        # Act
        response: httpx.Response = await client.get("/api/v1/runtimes/paper/versions")

        # Assert
        assert response.status_code == 502
        assert response.json()["detail"] == (
            "failed to fetch Paper versions from https://fill.papermc.io/v3/projects/paper"
        )
    finally:
        app.dependency_overrides.pop(get_runtime_registry, None)
