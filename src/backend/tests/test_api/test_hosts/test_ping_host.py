"""
test_ping_host.py

Integration tests for pinging hosts through the HTTP API.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    HostUnreachableError,
    SSHAuthError,
)
from fourdrinier.hosts.docker.operations import ping as docker_ping
from fourdrinier.hosts.docker.operations.ping import DockerPingObservation
from fourdrinier.hosts.docker.types import ObservedHostKey
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.operations import ping as kubernetes_ping
from fourdrinier.hosts.kubernetes.operations.ping import KubernetesPingObservation
from tests.test_api.test_hosts.support import FAKE_TOKEN
from tests.test_api.types import HostFactory, JsonObject

FAKE_HOST_KEY: ObservedHostKey = ObservedHostKey(
    key_type="ssh-ed25519",
    key_b64="AAAAC3NzaC1lZDI1NTE5AAAAIFakeFakeFakeFakeFakeFakeFakeFakeFakeFakeFake",
    fingerprint="SHA256:fakefingerprint",
    first_seen=True,
)

FAKE_DOCKER_PING: DockerPingObservation = DockerPingObservation(
    latency_ms=12.3,
    docker_version="27.0.1",
    api_version="1.41",
    os="linux",
    arch="amd64",
    host_key=FAKE_HOST_KEY,
)

FAKE_KUBERNETES_PING: KubernetesPingObservation = KubernetesPingObservation(
    latency_ms=8.7,
    git_version="v1.31.4+k3s1",
    platform="linux/amd64",
    username="system:serviceaccount:fourdrinier:fourdrinier",
    namespace="fourdrinier",
)


async def test_ping_host_001_nominal_docker_observation_is_persisted(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 001 - Nominal
    Condition: A Docker host responds with a first-seen SSH host key
    Result: The API returns the observation and persists the trust and last-seen state
    """

    # Arrange
    def fake_ping(**kwargs: Any) -> DockerPingObservation:
        return FAKE_DOCKER_PING

    monkeypatch.setattr(docker_ping, "_ping_remote", fake_ping)
    host: JsonObject = await docker_host_factory()

    # Act
    response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")

    # Assert
    body: JsonObject = response.json()
    refreshed_response: httpx.Response = await client.get(f"/api/v1/hosts/{host['id']}")
    refreshed: JsonObject = refreshed_response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["docker_version"] == "27.0.1"
    assert body["host_key"]["first_seen"] is True
    assert body["host_key"]["fingerprint"] == FAKE_HOST_KEY.fingerprint
    assert refreshed["host_key_fingerprint"] == FAKE_HOST_KEY.fingerprint
    assert refreshed["last_seen_at"] is not None


async def test_ping_host_002_nominal_recorded_docker_key_is_reused(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 002 - Nominal
    Condition: A Docker host is pinged before and after its SSH host key is recorded
    Result: The second ping verifies the recorded key while the first has no known key
    """
    # Arrange
    known_keys: list[ObservedHostKey | None] = []

    def fake_ping(**kwargs: Any) -> DockerPingObservation:
        known_key: ObservedHostKey | None = kwargs["known_host_key"]
        known_keys.append(known_key)
        return FAKE_DOCKER_PING

    monkeypatch.setattr(docker_ping, "_ping_remote", fake_ping)
    host: JsonObject = await docker_host_factory()

    # Act
    first_response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")
    second_response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")

    # Assert
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert known_keys[0] is None
    assert known_keys[1] is not None
    assert known_keys[1].key_b64 == FAKE_HOST_KEY.key_b64


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(SSHAuthError("auth rejected"), 502, id="authentication"),
        pytest.param(HostUnreachableError("no route"), 502, id="unreachable"),
        pytest.param(HostKeyMismatchError("key changed"), 409, id="host-key"),
    ],
)
async def test_ping_host_003_anomalous_docker_provider_fails(
    client: httpx.AsyncClient,
    docker_host_factory: HostFactory,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    """Test 003 - Anomalous
    Condition: The Docker provider reports a connectivity or trust failure
    Result: The API maps the failure to HTTP and does not update last-seen state
    """

    # Arrange
    def fake_ping(**kwargs: Any) -> DockerPingObservation:
        raise error

    monkeypatch.setattr(docker_ping, "_ping_remote", fake_ping)
    host: JsonObject = await docker_host_factory()

    # Act
    response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")

    # Assert
    refreshed_response: httpx.Response = await client.get(f"/api/v1/hosts/{host['id']}")
    refreshed: JsonObject = refreshed_response.json()
    assert response.status_code == expected_status
    assert refreshed["last_seen_at"] is None


async def test_ping_host_004_nominal_kubernetes_observation_is_persisted(
    client: httpx.AsyncClient,
    kubernetes_host_factory: HostFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 004 - Nominal
    Condition: A Kubernetes host responds using its stored token and namespace
    Result: The API returns the observation and persists last-seen state
    """
    # Arrange
    captured: dict[str, Any] = {}

    async def fake_ping(**kwargs: Any) -> KubernetesPingObservation:
        captured.update(kwargs)
        return FAKE_KUBERNETES_PING

    monkeypatch.setattr(kubernetes_ping, "_ping_remote", fake_ping)
    host: JsonObject = await kubernetes_host_factory()

    # Act
    response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")

    # Assert
    body: JsonObject = response.json()
    refreshed_response: httpx.Response = await client.get(f"/api/v1/hosts/{host['id']}")
    refreshed: JsonObject = refreshed_response.json()
    assert response.status_code == 200
    assert body["status"] == "ok"
    assert body["type"] == "kubernetes"
    assert body["git_version"] == "v1.31.4+k3s1"
    assert body["username"] == FAKE_KUBERNETES_PING.username
    assert body["can_create_deployments"] is True
    assert captured["token"] == FAKE_TOKEN
    assert captured["namespace"] == "fourdrinier"
    assert refreshed["last_seen_at"] is not None


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        pytest.param(KubernetesAuthError("token rejected"), 502, id="authentication"),
        pytest.param(ClusterUnreachableError("no route"), 502, id="unreachable"),
        pytest.param(TLSVerificationError("untrusted cert"), 409, id="tls"),
        pytest.param(KubernetesRBACError("not allowed"), 403, id="permission"),
    ],
)
async def test_ping_host_005_anomalous_kubernetes_provider_fails(
    client: httpx.AsyncClient,
    kubernetes_host_factory: HostFactory,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
) -> None:
    """Test 005 - Anomalous
    Condition: The Kubernetes provider reports a connectivity, trust, or permission failure
    Result: The API maps the failure to HTTP and does not update last-seen state
    """

    # Arrange
    async def fake_ping(**kwargs: Any) -> KubernetesPingObservation:
        raise error

    monkeypatch.setattr(kubernetes_ping, "_ping_remote", fake_ping)
    host: JsonObject = await kubernetes_host_factory()

    # Act
    response: httpx.Response = await client.post(f"/api/v1/hosts/{host['id']}/ping")

    # Assert
    refreshed_response: httpx.Response = await client.get(f"/api/v1/hosts/{host['id']}")
    refreshed: JsonObject = refreshed_response.json()
    assert response.status_code == expected_status
    assert refreshed["last_seen_at"] is None


async def test_ping_host_006_anomalous_host_does_not_exist(
    client: httpx.AsyncClient,
) -> None:
    """Test 006 - Anomalous
    Condition: No host exists for the requested identifier
    Result: The API returns HTTP 404
    """
    # Arrange
    missing_id: str = "00000000-0000-0000-0000-000000000000"

    # Act
    response: httpx.Response = await client.post(f"/api/v1/hosts/{missing_id}/ping")

    # Assert
    assert response.status_code == 404
