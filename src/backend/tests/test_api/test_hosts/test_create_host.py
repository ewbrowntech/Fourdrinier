"""
test_create_host.py

Integration tests for creating hosts through the HTTP API.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from tests.test_api.test_hosts.support import CA_PEM, FAKE_TOKEN
from tests.test_api.types import HostFactory, JsonObject


async def test_create_host_001_nominal_docker_host_is_returned(
    docker_host_factory: HostFactory,
) -> None:
    """Test 001 - Nominal
    Condition: A valid Docker host payload references an existing keypair
    Result: The API returns the created Docker host without connectivity observations
    """
    # Arrange
    expected_type: str = "docker"

    # Act
    host: JsonObject = await docker_host_factory()

    # Assert
    assert host["type"] == expected_type
    assert host["port"] == 22
    assert host["host_key_fingerprint"] is None
    assert host["last_seen_at"] is None


async def test_create_host_002_nominal_kubernetes_secrets_are_omitted(
    kubernetes_host_factory: HostFactory,
) -> None:
    """Test 002 - Nominal
    Condition: A valid Kubernetes host payload contains credentials and trust material
    Result: The API returns the host without exposing secret or bulky trust fields
    """
    # Arrange
    expected_api_url: str = "https://203.0.113.20:6443"

    # Act
    host: JsonObject = await kubernetes_host_factory()

    # Assert
    assert host["type"] == "kubernetes"
    assert host["api_url"] == expected_api_url
    assert host["namespace"] == "fourdrinier"
    assert host["enabled"] is True
    assert host["last_seen_at"] is None
    assert "token" not in host
    assert "token_encrypted" not in host
    assert "ca_cert_pem" not in host


async def test_create_host_003_anomalous_docker_keypair_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    """Test 003 - Anomalous
    Condition: A Docker host payload references a keypair that does not exist
    Result: The API returns HTTP 404
    """
    # Arrange
    payload: JsonObject = {
        "type": "docker",
        "name": "missing-keypair",
        "address": "203.0.113.10",
        "username": "docker",
        "keypair_id": "00000000-0000-0000-0000-000000000000",
    }

    # Act
    response: httpx.Response = await client.post("/api/v1/hosts", json=payload)

    # Assert
    assert response.status_code == 404


async def test_create_host_004_anomalous_docker_username_cannot_form_ssh_url(
    client: httpx.AsyncClient,
) -> None:
    """Test 004 - Anomalous
    Condition: A Docker host username contains a URL delimiter
    Result: The API returns HTTP 422
    """
    # Arrange
    keypair_response: httpx.Response = await client.post(
        "/api/v1/keypairs",
        json={"name": "username-keypair"},
    )
    keypair: JsonObject = keypair_response.json()
    payload: JsonObject = {
        "type": "docker",
        "name": "invalid-username",
        "address": "203.0.113.10",
        "username": "evil@user",
        "keypair_id": keypair["id"],
    }

    # Act
    response: httpx.Response = await client.post("/api/v1/hosts", json=payload)

    # Assert
    assert response.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"api_url": "http://203.0.113.20:6443"}, id="insecure-url"),
        pytest.param({"ca_cert_pem": "not a certificate"}, id="invalid-ca"),
        pytest.param({"namespace": "Not_Valid"}, id="invalid-namespace"),
    ],
)
async def test_create_host_005_anomalous_kubernetes_payload_is_invalid(
    client: httpx.AsyncClient,
    overrides: dict[str, Any],
) -> None:
    """Test 005 - Anomalous
    Condition: A Kubernetes host field violates its public schema
    Result: The API returns HTTP 422
    """
    # Arrange
    payload: JsonObject = {
        "type": "kubernetes",
        "name": "invalid-kubernetes",
        "api_url": "https://203.0.113.20:6443",
        "ca_cert_pem": CA_PEM,
        "token": FAKE_TOKEN,
        **overrides,
    }

    # Act
    response: httpx.Response = await client.post("/api/v1/hosts", json=payload)

    # Assert
    assert response.status_code == 422


async def test_create_host_006_anomalous_name_already_exists(
    client: httpx.AsyncClient,
    kubernetes_host_factory: HostFactory,
) -> None:
    """Test 006 - Anomalous
    Condition: A Kubernetes host already uses the requested name
    Result: The API returns HTTP 409
    """
    # Arrange
    await kubernetes_host_factory(name="duplicate")
    payload: JsonObject = {
        "type": "kubernetes",
        "name": "duplicate",
        "api_url": "https://203.0.113.21:6443",
        "ca_cert_pem": CA_PEM,
        "token": FAKE_TOKEN,
    }

    # Act
    response: httpx.Response = await client.post("/api/v1/hosts", json=payload)

    # Assert
    assert response.status_code == 409


@pytest.mark.parametrize(
    "existing_type",
    [
        pytest.param("docker", id="docker-then-kubernetes"),
        pytest.param("kubernetes", id="kubernetes-then-docker"),
    ],
)
async def test_create_host_007_anomalous_other_provider_uses_name(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    kubernetes_host_factory: HostFactory,
    existing_type: str,
) -> None:
    """Test 007 - Anomalous
    Condition: A host of the other provider type already uses the requested name
    Result: The API returns HTTP 409
    """
    # Arrange
    name: str = "shared"
    payload: JsonObject
    if existing_type == "docker":
        await docker_host_factory(name=name)
        payload = {
            "type": "kubernetes",
            "name": name,
            "api_url": "https://203.0.113.20:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
        }
    else:
        await kubernetes_host_factory(name=name)
        keypair_response: httpx.Response = await client.post(
            "/api/v1/keypairs",
            json={"name": "shared-keypair"},
        )
        keypair: JsonObject = keypair_response.json()
        payload = {
            "type": "docker",
            "name": name,
            "address": "203.0.113.10",
            "username": "docker",
            "keypair_id": keypair["id"],
        }

    # Act
    response: httpx.Response = await client.post("/api/v1/hosts", json=payload)

    # Assert
    assert response.status_code == 409
