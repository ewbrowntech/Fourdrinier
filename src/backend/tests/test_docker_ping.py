"""Unit tests for the Docker ping operation's blocking remote boundary."""

from __future__ import annotations

from typing import Any

import paramiko
import pytest

from fourdrinier.hosts.docker.client import KnownHostKey, host_key_entry_name
from fourdrinier.hosts.docker.errors import HostKeyMismatchError, SSHAuthError
from fourdrinier.hosts.docker.operations import ping as docker_ping
from fourdrinier.hosts.docker.operations.ping import DockerPingObservation
from fourdrinier.hosts.ssh.keys import generate_keypair, load_pkey


def _pkey_pem() -> str:
    private_key_pem: str = generate_keypair().private_key_pem
    return private_key_pem


def _server_key() -> paramiko.PKey:
    server_key: paramiko.PKey = load_pkey(_pkey_pem())
    return server_key


class _FakeAdapter:
    def __init__(self, captured: paramiko.PKey | None) -> None:
        self._captured: paramiko.PKey | None = captured

    @property
    def captured_host_key(self) -> paramiko.PKey | None:
        return self._captured


class _FakeClient:
    def __init__(self) -> None:
        self.closed: bool = False

    def ping(self) -> bool:
        return True

    def version(self) -> dict[str, Any]:
        return {"Version": "27.0.1", "ApiVersion": "1.41", "Os": "linux", "Arch": "amd64"}

    def close(self) -> None:
        self.closed = True


def _run_ping(
    monkeypatch: pytest.MonkeyPatch,
    *,
    captured: paramiko.PKey | None,
    known: KnownHostKey | None,
) -> tuple[DockerPingObservation, _FakeClient]:
    fake_client: _FakeClient = _FakeClient()

    def fake_build(**_kwargs: Any) -> tuple[_FakeClient, _FakeAdapter]:
        return fake_client, _FakeAdapter(captured)

    monkeypatch.setattr(docker_ping, "build_docker_client", fake_build)
    result: DockerPingObservation = docker_ping._ping_remote(
        address="203.0.113.10",
        port=22,
        username="docker",
        private_key_pem=_pkey_pem(),
        known_host_key=known,
    )
    return result, fake_client


def test_host_key_entry_name_001_nominal_default_and_custom_ports() -> None:
    """Test 001 - Nominal
    Condition: Docker SSH endpoints use the default or a custom port
    Result: Known-host entry names follow the OpenSSH host and port forms
    """
    # Arrange
    default_port: int = 22
    custom_port: int = 2222

    # Act
    default_entry: str = host_key_entry_name("example.com", default_port)
    custom_entry: str = host_key_entry_name("example.com", custom_port)

    # Assert
    assert default_entry == "example.com"
    assert custom_entry == "[example.com]:2222"


def test_docker_ping_remote_002_nominal_first_connection_captures_host_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 002 - Nominal
    Condition: The first SSH connection presents an unrecorded host key
    Result: The operation captures the key and closes the Docker client
    """
    # Arrange
    server_key: paramiko.PKey = _server_key()

    # Act
    result: DockerPingObservation
    fake_client: _FakeClient
    result, fake_client = _run_ping(monkeypatch, captured=server_key, known=None)

    # Assert
    assert result.host_key.first_seen is True
    assert result.host_key.key_b64 == server_key.get_base64()
    assert result.host_key.fingerprint == server_key.fingerprint
    assert result.docker_version == "27.0.1"
    assert fake_client.closed is True


def test_docker_ping_remote_003_nominal_recorded_key_is_verified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 003 - Nominal
    Condition: Paramiko verifies a previously recorded key without recapturing it
    Result: The recorded key is returned as a verified observation
    """
    # Arrange
    server_key: paramiko.PKey = _server_key()
    known: KnownHostKey = KnownHostKey(
        key_type=server_key.get_name(),
        key_b64=server_key.get_base64(),
    )

    # Act
    result: DockerPingObservation
    _fake_client: _FakeClient
    result, _fake_client = _run_ping(monkeypatch, captured=None, known=known)

    # Assert
    assert result.host_key.first_seen is False
    assert result.host_key.fingerprint == server_key.fingerprint


def test_docker_ping_remote_004_anomalous_captured_key_differs_from_recorded_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 004 - Anomalous
    Condition: SSH captures a key that differs from the previously recorded key
    Result: HostKeyMismatchError is raised
    """
    # Arrange
    recorded: paramiko.PKey = _server_key()
    different: paramiko.PKey = _server_key()
    known: KnownHostKey = KnownHostKey(
        key_type=recorded.get_name(),
        key_b64=recorded.get_base64(),
    )

    # Act / Assert
    with pytest.raises(HostKeyMismatchError):
        _run_ping(monkeypatch, captured=different, known=known)


def test_docker_ping_remote_005_anomalous_ssh_rejects_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 005 - Anomalous
    Condition: Paramiko reports an authentication failure while connecting
    Result: SSHAuthError is raised
    """

    # Arrange
    def fake_build(**_kwargs: Any) -> Any:
        raise paramiko.AuthenticationException("denied")

    monkeypatch.setattr(docker_ping, "build_docker_client", fake_build)

    # Act / Assert
    with pytest.raises(SSHAuthError):
        docker_ping._ping_remote(
            address="203.0.113.10",
            port=22,
            username="docker",
            private_key_pem=_pkey_pem(),
            known_host_key=None,
        )
