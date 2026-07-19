"""
test_get_keypair.py

Integration tests for retrieving SSH keypairs through the HTTP API.
"""

from __future__ import annotations

import httpx

from tests.test_api.types import JsonObject, KeypairFactory


async def test_get_keypair_001_nominal_keypair_exists(
    client: httpx.AsyncClient,
    keypair_factory: KeypairFactory,
) -> None:
    """Test 001 - Nominal
    Condition: A keypair exists for the requested identifier
    Result: The API returns that keypair
    """
    # Arrange
    created: JsonObject = await keypair_factory("retrieved")

    # Act
    response: httpx.Response = await client.get(f"/api/v1/keypairs/{created['id']}")

    # Assert
    keypair: JsonObject = response.json()
    assert response.status_code == 200
    assert keypair["id"] == created["id"]
    assert keypair["name"] == "retrieved"
