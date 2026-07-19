"""
test_get_host.py

Integration tests for retrieving hosts through the HTTP API.
"""

from __future__ import annotations

import httpx
import pytest

from tests.test_api.types import HostFactory, JsonObject


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param("docker", id="docker"),
        pytest.param("kubernetes", id="kubernetes"),
    ],
)
async def test_get_host_001_nominal_host_exists(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    kubernetes_host_factory: HostFactory,
    host_type: str,
) -> None:
    """Test 001 - Nominal
    Condition: A host of the requested provider type exists
    Result: The API returns that host
    """
    # Arrange
    factory: HostFactory = docker_host_factory if host_type == "docker" else kubernetes_host_factory
    created: JsonObject = await factory()

    # Act
    response: httpx.Response = await client.get(f"/api/v1/hosts/{created['id']}")

    # Assert
    host: JsonObject = response.json()
    assert response.status_code == 200
    assert host["id"] == created["id"]
    assert host["type"] == host_type


async def test_get_host_002_anomalous_host_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    """Test 002 - Anomalous
    Condition: No host exists for the requested identifier
    Result: The API returns HTTP 404
    """
    # Arrange
    missing_id: str = "00000000-0000-0000-0000-000000000000"

    # Act
    response: httpx.Response = await client.get(f"/api/v1/hosts/{missing_id}")

    # Assert
    assert response.status_code == 404
