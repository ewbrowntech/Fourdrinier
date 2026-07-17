"""
test_update_host.py

Integration tests for modifying hosts through the HTTP API.
"""

from __future__ import annotations

import uuid
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.core.crypto import FernetSecretCipher
from fourdrinier.core.secrets import EncryptedSecret, PlaintextSecret
from fourdrinier.db.models import KubernetesHostDetails
from tests.test_api.test_hosts.support import CA_PEM
from tests.test_api.types import HostFactory, JsonObject


async def test_update_host_001_nominal_docker_fields_and_credential_are_modified(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
) -> None:
    """Test 001 - Nominal
    Condition: A Docker patch supplies common, connection, and SSH credential fields
    Result: The API returns and persists every requested public modification
    """
    # Arrange
    host: JsonObject = await docker_host_factory(name="docker-original")
    keypair_response: httpx.Response = await client.post(
        "/api/v1/keypairs",
        json={"name": "replacement-keypair"},
    )
    keypair: JsonObject = keypair_response.json()
    payload: JsonObject = {
        "type": "docker",
        "name": "docker-updated",
        "enabled": False,
        "labels": {"environment": "staging"},
        "address": "203.0.113.11",
        "port": 2222,
        "username": "deploy",
        "keypair_id": keypair["id"],
    }

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/hosts/{host['id']}",
        json=payload,
    )

    # Assert
    updated: JsonObject = response.json()
    assert response.status_code == 200
    assert updated["id"] == host["id"]
    assert updated["name"] == "docker-updated"
    assert updated["enabled"] is False
    assert updated["labels"] == {"environment": "staging"}
    assert updated["address"] == "203.0.113.11"
    assert updated["port"] == 2222
    assert updated["username"] == "deploy"
    assert updated["keypair_id"] == keypair["id"]
    assert updated["updated_at"] >= host["updated_at"]


async def test_update_host_002_nominal_kubernetes_fields_and_credential_are_modified(
    app: FastAPI,
    client: httpx.AsyncClient,
    kubernetes_host_factory: HostFactory,
) -> None:
    """Test 002 - Nominal
    Condition: A Kubernetes patch supplies connection, trust, and token credential fields
    Result: Public modifications are returned while all credential material remains omitted
    """
    # Arrange
    host: JsonObject = await kubernetes_host_factory(name="kubernetes-original")
    payload: JsonObject = {
        "type": "kubernetes",
        "api_url": "https://203.0.113.21:6443",
        "ca_cert_pem": CA_PEM,
        "token": "replacement-service-account-token",
        "namespace": "staging",
    }

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/hosts/{host['id']}",
        json=payload,
    )

    # Assert
    updated: JsonObject = response.json()
    assert response.status_code == 200
    assert updated["api_url"] == "https://203.0.113.21:6443"
    assert updated["namespace"] == "staging"
    assert "token" not in updated
    assert "token_encrypted" not in updated
    assert "ca_cert_pem" not in updated
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        details: KubernetesHostDetails | None = await session.get(
            KubernetesHostDetails,
            uuid.UUID(str(host["id"])),
        )
    assert details is not None
    cipher: FernetSecretCipher = FernetSecretCipher.from_settings(app.state.settings)
    plaintext: PlaintextSecret = cipher.decrypt(EncryptedSecret(details.token_encrypted))
    assert plaintext == b"replacement-service-account-token"


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    [
        pytest.param("missing-host", 404, id="missing-host"),
        pytest.param("missing-keypair", 404, id="missing-keypair"),
        pytest.param("duplicate-name", 409, id="duplicate-name"),
        pytest.param("type-change", 409, id="type-change"),
    ],
)
async def test_update_host_003_anomalous_update_conflict_is_reported(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    kubernetes_host_factory: HostFactory,
    scenario: str,
    expected_status: int,
) -> None:
    """Test 003 - Anomalous
    Condition: The host, keypair, name, or matching provider prevents the requested update
    Result: The API returns the corresponding HTTP 404 or 409 response
    """
    # Arrange
    missing_id: str = "00000000-0000-0000-0000-000000000000"
    target_id: str = missing_id
    payload: JsonObject = {"type": "docker", "name": "updated"}
    if scenario != "missing-host":
        host: JsonObject = await docker_host_factory(name="target")
        target_id = str(host["id"])
    if scenario == "missing-keypair":
        payload = {"type": "docker", "keypair_id": missing_id}
    elif scenario == "duplicate-name":
        await kubernetes_host_factory(name="duplicate")
        payload = {"type": "docker", "name": "duplicate"}
    elif scenario == "type-change":
        payload = {"type": "kubernetes", "namespace": "staging"}

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/hosts/{target_id}",
        json=payload,
    )

    # Assert
    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"type": "docker", "keypair_id": None}, id="null-credential"),
        pytest.param({"type": "kubernetes", "token": ""}, id="empty-credential"),
        pytest.param(
            {"type": "docker", "token": "wrong-provider"},
            id="wrong-provider-credential",
        ),
    ],
)
async def test_update_host_004_anomalous_credential_payload_is_invalid(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    payload: dict[str, Any],
) -> None:
    """Test 004 - Anomalous
    Condition: A credential update is null, empty, or belongs to another provider
    Result: The API returns HTTP 422 without modifying the host
    """
    # Arrange
    host: JsonObject = await docker_host_factory()

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/hosts/{host['id']}",
        json=payload,
    )

    # Assert
    assert response.status_code == 422
