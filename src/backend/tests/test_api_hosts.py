"""API tests for /api/v1/hosts, with the SSH/docker layer mocked at the
blocking boundary so TOFU persistence still executes."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fourdrinier.hosts.docker import service as docker_service
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    HostUnreachableError,
    SSHAuthError,
)
from fourdrinier.hosts.docker.service import ObservedHostKey, PingResult

FAKE_HOST_KEY = ObservedHostKey(
    key_type="ssh-ed25519",
    key_b64="AAAAC3NzaC1lZDI1NTE5AAAAIFakeFakeFakeFakeFakeFakeFakeFakeFakeFakeFake",
    fingerprint="SHA256:fakefingerprint",
    first_seen=True,
)

FAKE_PING = PingResult(
    latency_ms=12.3,
    docker_version="27.0.1",
    api_version="1.41",
    os="linux",
    arch="amd64",
    host_key=FAKE_HOST_KEY,
)


async def _create_host(client: httpx.AsyncClient, **overrides: Any) -> dict[str, Any]:
    keypair = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    payload: dict[str, Any] = {
        "name": "remote",
        "address": "203.0.113.10",
        "port": 22,
        "username": "docker",
        "keypair_id": keypair["id"],
        **overrides,
    }
    resp = await client.post("/api/v1/hosts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_host(client: httpx.AsyncClient) -> None:
    host = await _create_host(client)
    assert host["type"] == "docker"
    assert host["port"] == 22
    assert host["host_key_fingerprint"] is None
    assert host["last_seen_at"] is None


async def test_create_host_unknown_keypair_is_404(client: httpx.AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "name": "h",
            "address": "203.0.113.10",
            "username": "docker",
            "keypair_id": "00000000-0000-0000-0000-000000000000",
        },
    )
    assert resp.status_code == 404


async def test_create_host_rejects_url_breaking_username(client: httpx.AsyncClient) -> None:
    keypair = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    resp = await client.post(
        "/api/v1/hosts",
        json={
            "name": "h",
            "address": "203.0.113.10",
            "username": "evil@user",
            "keypair_id": keypair["id"],
        },
    )
    assert resp.status_code == 422


async def test_list_get_delete_host(client: httpx.AsyncClient) -> None:
    host = await _create_host(client)
    assert [h["id"] for h in (await client.get("/api/v1/hosts")).json()] == [host["id"]]
    assert [h["id"] for h in (await client.get("/api/v1/hosts", params={"type": "docker"})).json()] == [
        host["id"]
    ]
    assert (await client.get("/api/v1/hosts", params={"type": "other"})).status_code == 422
    assert (await client.get(f"/api/v1/hosts/{host['id']}")).status_code == 200
    assert (await client.delete(f"/api/v1/hosts/{host['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/hosts/{host['id']}")).status_code == 404


async def test_ping_success_records_tofu_key(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(docker_service, "_ping_blocking", lambda **kwargs: FAKE_PING)
    host = await _create_host(client)

    resp = await client.post(f"/api/v1/hosts/{host['id']}/ping")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["docker_version"] == "27.0.1"
    assert body["host_key"]["first_seen"] is True
    assert body["host_key"]["fingerprint"] == FAKE_HOST_KEY.fingerprint

    refreshed = (await client.get(f"/api/v1/hosts/{host['id']}")).json()
    assert refreshed["host_key_fingerprint"] == FAKE_HOST_KEY.fingerprint
    assert refreshed["last_seen_at"] is not None


async def test_ping_passes_recorded_key_for_verification(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen_known_keys: list[Any] = []

    def fake_ping(**kwargs: Any) -> PingResult:
        seen_known_keys.append(kwargs["known_host_key"])
        return FAKE_PING

    monkeypatch.setattr(docker_service, "_ping_blocking", fake_ping)
    host = await _create_host(client)
    await client.post(f"/api/v1/hosts/{host['id']}/ping")
    await client.post(f"/api/v1/hosts/{host['id']}/ping")

    first, second = seen_known_keys
    assert first is None
    assert second is not None
    assert second.key_b64 == FAKE_HOST_KEY.key_b64


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (SSHAuthError("auth rejected"), 502),
        (HostUnreachableError("no route"), 502),
        (HostKeyMismatchError("key changed"), 409),
    ],
)
async def test_ping_error_mapping(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    def fake_ping(**kwargs: Any) -> PingResult:
        raise error

    monkeypatch.setattr(docker_service, "_ping_blocking", fake_ping)
    host = await _create_host(client)
    resp = await client.post(f"/api/v1/hosts/{host['id']}/ping")
    assert resp.status_code == expected_status
    assert (await client.get(f"/api/v1/hosts/{host['id']}")).json()["last_seen_at"] is None
