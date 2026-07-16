"""
test_delete_host.py

Integration tests for deleting hosts through the HTTP API.
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
async def test_delete_host_001_nominal_host_exists(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    kubernetes_host_factory: HostFactory,
    host_type: str,
) -> None:
    """Test 001 - Nominal
    Condition: A host of the requested provider type exists
    Result: The API deletes only that host and subsequent retrieval returns HTTP 404
    """
    # Arrange
    factory: HostFactory = docker_host_factory if host_type == "docker" else kubernetes_host_factory
    other_factory: HostFactory = (
        kubernetes_host_factory if host_type == "docker" else docker_host_factory
    )
    host: JsonObject = await factory(name="deleted")
    other_host: JsonObject = await other_factory(name="preserved")

    # Act
    response: httpx.Response = await client.delete(f"/api/v1/hosts/{host['id']}")

    # Assert
    get_response: httpx.Response = await client.get(f"/api/v1/hosts/{host['id']}")
    other_response: httpx.Response = await client.get(f"/api/v1/hosts/{other_host['id']}")
    assert response.status_code == 204
    assert get_response.status_code == 404
    assert other_response.status_code == 200
