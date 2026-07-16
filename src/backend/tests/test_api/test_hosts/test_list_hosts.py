"""
test_list_hosts.py

Integration tests for listing hosts through the HTTP API.
"""

from __future__ import annotations

import httpx
import pytest

from tests.test_api.types import HostFactory, JsonObject


@pytest.mark.parametrize(
    ("host_type", "expected_hosts"),
    [
        pytest.param(
            None,
            [("a-docker", "docker"), ("b-kubernetes", "kubernetes")],
            id="all",
        ),
        pytest.param("docker", [("a-docker", "docker")], id="docker"),
        pytest.param(
            "kubernetes",
            [("b-kubernetes", "kubernetes")],
            id="kubernetes",
        ),
    ],
)
async def test_list_hosts_001_nominal_hosts_are_ordered_and_filtered(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    kubernetes_host_factory: HostFactory,
    host_type: str | None,
    expected_hosts: list[tuple[str, str]],
) -> None:
    """Test 001 - Nominal
    Condition: Both provider types exist and an optional provider filter is supplied
    Result: Matching hosts are returned in deterministic name order
    """
    # Arrange
    await docker_host_factory(name="a-docker")
    await kubernetes_host_factory(name="b-kubernetes")
    params: dict[str, str] = {} if host_type is None else {"type": host_type}

    # Act
    response: httpx.Response = await client.get("/api/v1/hosts", params=params)

    # Assert
    hosts: list[JsonObject] = response.json()
    assert response.status_code == 200
    assert [(host["name"], host["type"]) for host in hosts] == expected_hosts


async def test_list_hosts_002_anomalous_provider_filter_is_unknown(
    client: httpx.AsyncClient,
) -> None:
    """Test 002 - Anomalous
    Condition: The provider filter is not a supported host type
    Result: The API returns HTTP 422
    """
    # Arrange
    params: dict[str, str] = {"type": "other"}

    # Act
    response: httpx.Response = await client.get("/api/v1/hosts", params=params)

    # Assert
    assert response.status_code == 422
