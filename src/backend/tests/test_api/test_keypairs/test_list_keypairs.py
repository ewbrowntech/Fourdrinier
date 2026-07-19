"""
test_list_keypairs.py

Integration tests for listing SSH keypairs through the HTTP API.
"""

from __future__ import annotations

import httpx

from tests.test_api.types import JsonObject, KeypairFactory


async def test_list_keypairs_001_nominal_keypairs_exist(
    client: httpx.AsyncClient,
    keypair_factory: KeypairFactory,
) -> None:
    """Test 001 - Nominal
    Condition: A generated keypair exists
    Result: The API includes that keypair in the list
    """
    # Arrange
    created: JsonObject = await keypair_factory("listed")

    # Act
    response: httpx.Response = await client.get("/api/v1/keypairs")

    # Assert
    keypairs: list[JsonObject] = response.json()
    assert response.status_code == 200
    assert [keypair["id"] for keypair in keypairs] == [created["id"]]
