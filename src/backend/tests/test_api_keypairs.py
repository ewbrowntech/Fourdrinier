"""API tests for /api/v1/keypairs."""

from __future__ import annotations

import httpx

from fourdrinier.hosts.ssh.keys import generate_keypair


async def test_generate_keypair(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/keypairs", json={"name": "gen"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "generated"
    assert body["algorithm"] == "ed25519"
    assert body["public_key"].startswith("ssh-ed25519 ")
    assert body["fingerprint"].startswith("SHA256:")
    assert "private_key" not in body
    assert "private_key_encrypted" not in body


async def test_upload_keypair(client: httpx.AsyncClient) -> None:
    material = generate_keypair()
    resp = await client.post(
        "/api/v1/keypairs",
        json={"name": "uploaded", "private_key": material.private_key_pem},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "uploaded"
    assert body["public_key"] == material.public_key


async def test_upload_invalid_key_is_422(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/keypairs", json={"name": "bad", "private_key": "garbage"})
    assert resp.status_code == 422


async def test_duplicate_name_is_409(client: httpx.AsyncClient) -> None:
    assert (await client.post("/api/v1/keypairs", json={"name": "dupe"})).status_code == 201
    resp = await client.post("/api/v1/keypairs", json={"name": "dupe"})
    assert resp.status_code == 409


async def test_list_and_get(client: httpx.AsyncClient) -> None:
    created = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    listed = (await client.get("/api/v1/keypairs")).json()
    assert [kp["id"] for kp in listed] == [created["id"]]
    fetched = await client.get(f"/api/v1/keypairs/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "kp"


async def test_delete(client: httpx.AsyncClient) -> None:
    created = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    assert (await client.delete(f"/api/v1/keypairs/{created['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/keypairs/{created['id']}")).status_code == 404


async def test_delete_in_use_is_409(client: httpx.AsyncClient) -> None:
    keypair = (await client.post("/api/v1/keypairs", json={"name": "kp"})).json()
    host = await client.post(
        "/api/v1/hosts",
        json={
            "name": "h1",
            "address": "203.0.113.10",
            "username": "docker",
            "keypair_id": keypair["id"],
        },
    )
    assert host.status_code == 201
    resp = await client.delete(f"/api/v1/keypairs/{keypair['id']}")
    assert resp.status_code == 409
