"""
conftest.py

Provide an HTTP-level logical server factory for API integration tests.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.test_api.types import JsonObject, ServerFactory


@pytest.fixture
def server_factory(client: httpx.AsyncClient) -> ServerFactory:
    """Create logical servers through the public API.

    Args:
        client: HTTP client connected to the test application.

    Returns:
        An asynchronous factory accepting server payload overrides.
    """

    async def create_server(**overrides: Any) -> JsonObject:
        payload: JsonObject = {"name": "pumpkin-patch", **overrides}
        response: httpx.Response = await client.post("/api/v1/servers", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create_server
