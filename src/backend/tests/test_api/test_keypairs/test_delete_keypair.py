"""
test_delete_keypair.py

Integration tests for deleting SSH keypairs through the HTTP API.
"""

from __future__ import annotations

import httpx

from tests.test_api.types import JsonObject, KeypairFactory


async def test_delete_keypair_001_nominal_keypair_exists(
    client: httpx.AsyncClient,
    keypair_factory: KeypairFactory,
) -> None:
    """Test 001 - Nominal
    Condition: A keypair exists for the requested identifier and is not in use
    Result: The API deletes the keypair and subsequent retrieval returns HTTP 404
    """
    # Arrange
    keypair: JsonObject = await keypair_factory("deleted")

    # Act
    response: httpx.Response = await client.delete(f"/api/v1/keypairs/{keypair['id']}")

    # Assert
    get_response: httpx.Response = await client.get(f"/api/v1/keypairs/{keypair['id']}")
    assert response.status_code == 204
    assert get_response.status_code == 404


async def test_delete_keypair_002_anomalous_keypair_is_in_use(
    client: httpx.AsyncClient,
    keypair_factory: KeypairFactory,
) -> None:
    """Test 002 - Anomalous
    Condition: A Docker host references the requested keypair
    Result: The API returns HTTP 409 and preserves the keypair
    """
    # Arrange
    keypair: JsonObject = await keypair_factory("in-use")
    host_payload: JsonObject = {
        "type": "docker",
        "name": "docker-host",
        "address": "203.0.113.10",
        "username": "docker",
        "keypair_id": keypair["id"],
    }
    host_response: httpx.Response = await client.post(
        "/api/v1/hosts",
        json=host_payload,
    )
    assert host_response.status_code == 201

    # Act
    response: httpx.Response = await client.delete(f"/api/v1/keypairs/{keypair['id']}")

    # Assert
    assert response.status_code == 409
