"""
test_server_crud.py

Integration tests for logical server CRUD through the HTTP API.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fourdrinier.servers import PUMPKIN_MINECRAFT_VERSION
from tests.test_api.types import JsonObject, ServerFactory


async def test_create_server_001_nominal_pumpkin_configuration_is_saved(
    client: httpx.AsyncClient,
) -> None:
    """Test 001 - Nominal
    Condition: A valid name and the fixed Pumpkin runtime are supplied
    Result: A stopped generation-one configuration is returned without host data
    """
    # Arrange
    payload: JsonObject = {"name": "lantern-grove", "runtime": "pumpkin"}

    # Act
    response: httpx.Response = await client.post("/api/v1/servers", json=payload)

    # Assert
    server: JsonObject = response.json()
    assert response.status_code == 201
    assert server["name"] == "lantern-grove"
    assert server["runtime"] == "pumpkin"
    assert server["minecraft_version"] == PUMPKIN_MINECRAFT_VERSION
    assert server["desired_state"] == "stopped"
    assert server["spec_generation"] == 1
    assert server["created_at"] is not None
    assert server["updated_at"] is not None
    assert "host_id" not in server
    assert "deployment" not in server


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"name": ""}, id="empty-name"),
        pytest.param({"name": "paper-world", "runtime": "paper"}, id="unsupported-runtime"),
        pytest.param({"name": "eager-world", "desired_state": "running"}, id="lifecycle-state"),
    ],
)
async def test_create_server_002_anomalous_payload_cannot_override_fixed_configuration(
    client: httpx.AsyncClient,
    payload: dict[str, Any],
) -> None:
    """Test 002 - Anomalous
    Condition: Creation has an empty name or attempts to select unsupported configuration
    Result: The API returns HTTP 422 without saving the server
    """
    # Arrange
    expected_status: int = 422

    # Act
    response: httpx.Response = await client.post("/api/v1/servers", json=payload)

    # Assert
    assert response.status_code == expected_status


async def test_create_server_003_anomalous_name_already_exists(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 003 - Anomalous
    Condition: Another logical server already uses the requested name
    Result: The API returns HTTP 409 and preserves the original server
    """
    # Arrange
    original: JsonObject = await server_factory(name="shared-world")
    payload: JsonObject = {"name": "shared-world"}

    # Act
    response: httpx.Response = await client.post("/api/v1/servers", json=payload)

    # Assert
    get_response: httpx.Response = await client.get(f"/api/v1/servers/{original['id']}")
    assert response.status_code == 409
    assert get_response.status_code == 200


async def test_list_servers_004_nominal_servers_are_returned_in_name_order(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 004 - Nominal
    Condition: Multiple logical servers have been saved in non-alphabetical order
    Result: The API returns every server in deterministic name order
    """
    # Arrange
    await server_factory(name="zucchini-zone")
    await server_factory(name="autumn-archive")

    # Act
    response: httpx.Response = await client.get("/api/v1/servers")

    # Assert
    servers: list[JsonObject] = response.json()
    assert response.status_code == 200
    assert [server["name"] for server in servers] == ["autumn-archive", "zucchini-zone"]


async def test_get_server_005_nominal_saved_configuration_exists(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 005 - Nominal
    Condition: A logical server exists with the requested identifier
    Result: The API returns that exact saved configuration
    """
    # Arrange
    created: JsonObject = await server_factory(name="inspection-world")

    # Act
    response: httpx.Response = await client.get(f"/api/v1/servers/{created['id']}")

    # Assert
    assert response.status_code == 200
    assert response.json() == created


async def test_get_server_006_anomalous_server_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    """Test 006 - Anomalous
    Condition: No logical server has the requested identifier
    Result: The API returns HTTP 404 with a stable not-found detail
    """
    # Arrange
    server_id: str = "00000000-0000-0000-0000-000000000000"

    # Act
    response: httpx.Response = await client.get(f"/api/v1/servers/{server_id}")

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": f"server {server_id} not found"}


async def test_update_server_007_nominal_name_changes_without_new_spec_generation(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 007 - Nominal
    Condition: A saved configuration receives a new display name
    Result: Only its name and update timestamp change while deployment intent is preserved
    """
    # Arrange
    created: JsonObject = await server_factory(name="before-rename")
    payload: JsonObject = {"name": "after-rename"}

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/servers/{created['id']}",
        json=payload,
    )

    # Assert
    updated: JsonObject = response.json()
    assert response.status_code == 200
    assert updated["id"] == created["id"]
    assert updated["name"] == "after-rename"
    assert updated["runtime"] == created["runtime"]
    assert updated["minecraft_version"] == created["minecraft_version"]
    assert updated["desired_state"] == created["desired_state"]
    assert updated["spec_generation"] == created["spec_generation"]
    assert updated["updated_at"] >= created["updated_at"]


async def test_update_server_008_nominal_empty_patch_preserves_configuration(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 008 - Nominal
    Condition: A partial update omits every editable field
    Result: The API accepts the no-op and preserves the logical configuration
    """
    # Arrange
    created: JsonObject = await server_factory(name="unchanged-world")
    payload: JsonObject = {}

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/servers/{created['id']}",
        json=payload,
    )

    # Assert
    updated: JsonObject = response.json()
    assert response.status_code == 200
    assert updated["name"] == created["name"]
    assert updated["spec_generation"] == created["spec_generation"]


@pytest.mark.parametrize(
    ("scenario", "expected_status"),
    [
        pytest.param("missing", 404, id="missing"),
        pytest.param("duplicate", 409, id="duplicate"),
        pytest.param("null-name", 422, id="null-name"),
        pytest.param("immutable-runtime", 422, id="immutable-runtime"),
    ],
)
async def test_update_server_009_anomalous_invalid_update_is_rejected(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
    scenario: str,
    expected_status: int,
) -> None:
    """Test 009 - Anomalous
    Condition: The target or payload prevents a valid logical server rename
    Result: The API returns the corresponding HTTP 404, 409, or 422 response
    """
    # Arrange
    target_id: str = "00000000-0000-0000-0000-000000000000"
    payload: JsonObject = {"name": "renamed"}
    if scenario != "missing":
        target: JsonObject = await server_factory(name="rename-target")
        target_id = str(target["id"])
    if scenario == "duplicate":
        await server_factory(name="name-in-use")
        payload = {"name": "name-in-use"}
    elif scenario == "null-name":
        payload = {"name": None}
    elif scenario == "immutable-runtime":
        payload = {"runtime": "pumpkin"}

    # Act
    response: httpx.Response = await client.patch(
        f"/api/v1/servers/{target_id}",
        json=payload,
    )

    # Assert
    assert response.status_code == expected_status


async def test_delete_server_010_nominal_saved_configuration_exists(
    client: httpx.AsyncClient,
    server_factory: ServerFactory,
) -> None:
    """Test 010 - Nominal
    Condition: A logical server configuration exists without a deployment
    Result: The API deletes it and subsequent retrieval returns HTTP 404
    """
    # Arrange
    created: JsonObject = await server_factory(name="temporary-world")

    # Act
    response: httpx.Response = await client.delete(f"/api/v1/servers/{created['id']}")

    # Assert
    get_response: httpx.Response = await client.get(f"/api/v1/servers/{created['id']}")
    assert response.status_code == 204
    assert get_response.status_code == 404


async def test_delete_server_011_anomalous_server_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    """Test 011 - Anomalous
    Condition: No logical server has the requested identifier
    Result: The API returns HTTP 404 and leaves the transaction usable
    """
    # Arrange
    server_id: str = "00000000-0000-0000-0000-000000000000"

    # Act
    response: httpx.Response = await client.delete(f"/api/v1/servers/{server_id}")

    # Assert
    list_response: httpx.Response = await client.get("/api/v1/servers")
    assert response.status_code == 404
    assert list_response.status_code == 200
