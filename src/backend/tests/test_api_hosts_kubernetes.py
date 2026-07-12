"""API tests for kubernetes hosts on /api/v1/hosts, with the HTTPS layer
mocked at the ``_ping_cluster`` boundary so persistence still executes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID

from fourdrinier.hosts.kubernetes import service as k8s_service
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.service import PingResult

FAKE_TOKEN = "eyJhbGciOiJSUzI1NiJ9.fake.token"

FAKE_PING = PingResult(
    latency_ms=8.7,
    git_version="v1.31.4+k3s1",
    platform="linux/amd64",
    username="system:serviceaccount:fourdrinier:fourdrinier",
    namespace="fourdrinier",
)


def _make_ca_pem() -> str:
    """Generate a minimal self-signed CA certificate PEM."""
    key = ed25519.Ed25519PrivateKey.generate()
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + timedelta(days=1))
        .sign(key, algorithm=None)
    )
    return cert.public_bytes(Encoding.PEM).decode()


CA_PEM = _make_ca_pem()


async def _create_k8s_host(
    client: httpx.AsyncClient, **overrides: Any
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "kubernetes",
        "name": "k3s",
        "api_url": "https://203.0.113.20:6443",
        "ca_cert_pem": CA_PEM,
        "token": FAKE_TOKEN,
        **overrides,
    }
    resp = await client.post("/api/v1/hosts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_docker_host(
    client: httpx.AsyncClient, **overrides: Any
) -> dict[str, Any]:
    keypair = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    payload: dict[str, Any] = {
        "name": "remote",
        "address": "203.0.113.10",
        "username": "docker",
        "keypair_id": keypair["id"],
        **overrides,
    }
    resp = await client.post("/api/v1/hosts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_kubernetes_host(client: httpx.AsyncClient) -> None:
    host = await _create_k8s_host(client)
    assert host["type"] == "kubernetes"
    assert host["api_url"] == "https://203.0.113.20:6443"
    assert host["namespace"] == "fourdrinier"
    assert host["enabled"] is True
    assert host["last_seen_at"] is None
    # secrets and bulky material never leave the API
    assert "token" not in host
    assert "token_encrypted" not in host
    assert "ca_cert_pem" not in host


async def test_create_rejects_http_url(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "type": "kubernetes",
            "name": "k3s",
            "api_url": "http://203.0.113.20:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
        },
    )
    assert resp.status_code == 422


async def test_create_rejects_invalid_ca(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "type": "kubernetes",
            "name": "k3s",
            "api_url": "https://203.0.113.20:6443",
            "ca_cert_pem": "not a certificate",
            "token": FAKE_TOKEN,
        },
    )
    assert resp.status_code == 422


async def test_create_rejects_bad_namespace(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "type": "kubernetes",
            "name": "k3s",
            "api_url": "https://203.0.113.20:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
            "namespace": "Not_Valid",
        },
    )
    assert resp.status_code == 422


async def test_duplicate_name_conflict(client: httpx.AsyncClient) -> None:
    await _create_k8s_host(client)
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "type": "kubernetes",
            "name": "k3s",
            "api_url": "https://203.0.113.21:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
        },
    )
    assert resp.status_code == 409


async def test_name_conflict_across_types(client: httpx.AsyncClient) -> None:
    # kubernetes name blocks a docker host of the same name…
    await _create_k8s_host(client, name="shared")
    keypair = (await client.post("/api/v1/keypairs", json={"name": "kp2"})).json()
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "name": "shared",
            "address": "203.0.113.10",
            "username": "docker",
            "keypair_id": keypair["id"],
        },
    )
    assert resp.status_code == 409

    # …and a docker name blocks a kubernetes host of the same name.
    await _create_docker_host(client, name="shared2")
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "type": "kubernetes",
            "name": "shared2",
            "api_url": "https://203.0.113.20:6443",
            "ca_cert_pem": CA_PEM,
            "token": FAKE_TOKEN,
        },
    )
    assert resp.status_code == 409


async def test_list_merges_both_types(client: httpx.AsyncClient) -> None:
    docker_host = await _create_docker_host(client, name="a-docker")
    k8s_host = await _create_k8s_host(client, name="b-k3s")

    merged = (await client.get("/api/v1/hosts")).json()
    assert [(h["name"], h["type"]) for h in merged] == [
        ("a-docker", "docker"),
        ("b-k3s", "kubernetes"),
    ]

    only_k8s = (await client.get("/api/v1/hosts", params={"type": "kubernetes"})).json()
    assert [h["id"] for h in only_k8s] == [k8s_host["id"]]

    only_docker = (await client.get("/api/v1/hosts", params={"type": "docker"})).json()
    assert [h["id"] for h in only_docker] == [docker_host["id"]]

    assert (await client.get("/api/v1/hosts", params={"type": "other"})).status_code == 422


async def test_get_delete_kubernetes_host(client: httpx.AsyncClient) -> None:
    docker_host = await _create_docker_host(client)
    host = await _create_k8s_host(client)

    assert (await client.get(f"/api/v1/hosts/{host['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/hosts/{host['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/hosts/{host['id']}")).status_code == 404
    # the docker host is untouched
    assert (await client.get(f"/api/v1/hosts/{docker_host['id']}")).status_code == 200


async def test_ping_success_records_last_seen(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    async def fake_ping(**kwargs: Any) -> PingResult:
        captured.update(kwargs)
        return FAKE_PING

    monkeypatch.setattr(k8s_service, "_ping_cluster", fake_ping)
    host = await _create_k8s_host(client)

    resp = await client.post(f"/api/v1/hosts/{host['id']}/ping")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["type"] == "kubernetes"
    assert body["git_version"] == "v1.31.4+k3s1"
    assert body["username"] == FAKE_PING.username
    assert body["can_create_deployments"] is True

    # the stored token round-trips through encrypt/decrypt
    assert captured["token"] == FAKE_TOKEN
    assert captured["namespace"] == "fourdrinier"

    refreshed = (await client.get(f"/api/v1/hosts/{host['id']}")).json()
    assert refreshed["last_seen_at"] is not None


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (KubernetesAuthError("token rejected"), 502),
        (ClusterUnreachableError("no route"), 502),
        (TLSVerificationError("untrusted cert"), 409),
        (KubernetesRBACError("not allowed"), 403),
    ],
)
async def test_ping_error_mapping(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    async def fake_ping(**kwargs: Any) -> PingResult:
        raise error

    monkeypatch.setattr(k8s_service, "_ping_cluster", fake_ping)
    host = await _create_k8s_host(client)
    resp = await client.post(f"/api/v1/hosts/{host['id']}/ping")
    assert resp.status_code == expected_status
    assert (await client.get(f"/api/v1/hosts/{host['id']}")).json()["last_seen_at"] is None


async def test_ping_missing_host_404(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/hosts/00000000-0000-0000-0000-000000000000/ping"
    )
    assert resp.status_code == 404
