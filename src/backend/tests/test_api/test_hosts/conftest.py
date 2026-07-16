"""
conftest.py

Provide HTTP-level host factories for host API integration tests.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.test_api.test_hosts.support import CA_PEM, FAKE_TOKEN
from tests.test_api.types import HostFactory, JsonObject


@pytest.fixture
def docker_host_factory(client: httpx.AsyncClient) -> HostFactory:
    """Create Docker hosts through the public API.

    Args:
        client: HTTP client connected to the test application.

    Returns:
        An asynchronous factory accepting host payload overrides.
    """

    async def create_docker_host(**overrides: Any) -> JsonObject:
        name: str = overrides.get("name", "remote")
        keypair_response: httpx.Response = await client.post(
            "/api/v1/keypairs",
            json={"name": f"{name}-keypair"},
        )
        keypair: JsonObject = keypair_response.json()
        payload: JsonObject = {
            "type": "docker",
            "name": name,
            "address": "203.0.113.10",
            "port": 22,
            "username": "docker",
            "keypair_id": keypair["id"],
            **overrides,
        }
        response: httpx.Response = await client.post("/api/v1/hosts", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create_docker_host


@pytest.fixture
def kubernetes_host_factory(client: httpx.AsyncClient) -> HostFactory:
    """Create Kubernetes hosts through the public API.

    Args:
        client: HTTP client connected to the test application.

    Returns:
        An asynchronous factory accepting host payload overrides.
    """

    async def create_kubernetes_host(**overrides: Any) -> JsonObject:
        payload: JsonObject = {
            "type": "kubernetes",
            "name": "k3s",
            "api_url": "https://203.0.113.20:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
            **overrides,
        }
        response: httpx.Response = await client.post("/api/v1/hosts", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return create_kubernetes_host
