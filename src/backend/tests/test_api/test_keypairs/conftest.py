"""
conftest.py

Provide an HTTP-level keypair factory for keypair API integration tests.
"""

from __future__ import annotations

import httpx
import pytest

from tests.test_api.types import JsonObject, KeypairFactory


@pytest.fixture
def keypair_factory(client: httpx.AsyncClient) -> KeypairFactory:
    """Create generated keypairs through the public API.

    Args:
        client: HTTP client connected to the test application.

    Returns:
        An asynchronous factory accepting a keypair name.
    """

    async def create_keypair(name: str) -> JsonObject:
        response: httpx.Response = await client.post(
            "/api/v1/keypairs",
            json={"name": name},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return create_keypair
