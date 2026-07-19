"""
test_create_keypair.py

Integration tests for creating SSH keypairs through the HTTP API.
"""

from __future__ import annotations

import httpx

from fourdrinier.hosts.ssh.keys import KeypairMaterial, generate_keypair
from tests.test_api.types import JsonObject, KeypairFactory


async def test_create_keypair_001_nominal_private_key_is_generated(
    client: httpx.AsyncClient,
) -> None:
    """Test 001 - Nominal
    Condition: A keypair name is supplied without private key material
    Result: The API returns generated public metadata without exposing the private key
    """
    # Arrange
    payload: JsonObject = {"name": "generated"}

    # Act
    response: httpx.Response = await client.post("/api/v1/keypairs", json=payload)

    # Assert
    body: JsonObject = response.json()
    assert response.status_code == 201
    assert body["source"] == "generated"
    assert body["algorithm"] == "ed25519"
    assert body["public_key"].startswith("ssh-ed25519 ")
    assert body["fingerprint"].startswith("SHA256:")
    assert "private_key" not in body
    assert "private_key_encrypted" not in body


async def test_create_keypair_002_nominal_private_key_is_uploaded(
    client: httpx.AsyncClient,
) -> None:
    """Test 002 - Nominal
    Condition: Valid private key material is supplied with a keypair name
    Result: The API imports the keypair and returns its matching public key
    """
    # Arrange
    material: KeypairMaterial = generate_keypair()
    payload: JsonObject = {
        "name": "uploaded",
        "private_key": material.private_key_pem,
    }

    # Act
    response: httpx.Response = await client.post("/api/v1/keypairs", json=payload)

    # Assert
    body: JsonObject = response.json()
    assert response.status_code == 201
    assert body["source"] == "uploaded"
    assert body["public_key"] == material.public_key


async def test_create_keypair_003_anomalous_private_key_is_invalid(
    client: httpx.AsyncClient,
) -> None:
    """Test 003 - Anomalous
    Condition: The supplied private key is not valid key material
    Result: The API returns HTTP 422
    """
    # Arrange
    payload: JsonObject = {"name": "invalid", "private_key": "garbage"}

    # Act
    response: httpx.Response = await client.post("/api/v1/keypairs", json=payload)

    # Assert
    assert response.status_code == 422


async def test_create_keypair_004_anomalous_name_already_exists(
    client: httpx.AsyncClient,
    keypair_factory: KeypairFactory,
) -> None:
    """Test 004 - Anomalous
    Condition: A keypair already uses the requested name
    Result: The API returns HTTP 409
    """
    # Arrange
    await keypair_factory("duplicate")
    payload: JsonObject = {"name": "duplicate"}

    # Act
    response: httpx.Response = await client.post("/api/v1/keypairs", json=payload)

    # Assert
    assert response.status_code == 409
