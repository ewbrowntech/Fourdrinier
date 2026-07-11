"""Unit tests for the blocking docker-over-SSH layer (connection mocked)."""

from __future__ import annotations

from typing import Any

import paramiko
import pytest

from fourdrinier.hosts.docker import service as docker_service
from fourdrinier.hosts.docker.client import KnownHostKey, host_key_entry_name
from fourdrinier.hosts.docker.errors import HostKeyMismatchError, SSHAuthError
from fourdrinier.hosts.ssh.keys import generate_keypair, load_pkey


def _pkey_pem() -> str:
    return generate_keypair().private_key_pem


def _server_key() -> paramiko.PKey:
    return load_pkey(_pkey_pem())


class FakeAdapter:
    def __init__(self, captured: paramiko.PKey | None) -> None:
        self._captured = captured

    @property
    def captured_host_key(self) -> paramiko.PKey | None:
        return self._captured


class FakeClient:
    def __init__(self) -> None:
        self.closed = False

    def ping(self) -> bool:
        return True

    def version(self) -> dict[str, Any]:
        return {"Version": "27.0.1", "ApiVersion": "1.41", "Os": "linux", "Arch": "amd64"}

    def close(self) -> None:
        self.closed = True


def test_host_key_entry_name() -> None:
    assert host_key_entry_name("example.com", 22) == "example.com"
    assert host_key_entry_name("example.com", 2222) == "[example.com]:2222"


def _run_ping(
    monkeypatch: pytest.MonkeyPatch,
    *,
    captured: paramiko.PKey | None,
    known: KnownHostKey | None,
) -> tuple[docker_service.PingResult, FakeClient]:
    fake_client = FakeClient()

    def fake_build(**kwargs: Any) -> tuple[FakeClient, FakeAdapter]:
        return fake_client, FakeAdapter(captured)

    monkeypatch.setattr(docker_service, "build_docker_client", fake_build)
    result = docker_service._ping_blocking(
        address="203.0.113.10",
        port=22,
        username="docker",
        private_key_pem=_pkey_pem(),
        known_host_key=known,
    )
    return result, fake_client


def test_first_connection_captures_host_key(monkeypatch: pytest.MonkeyPatch) -> None:
    server_key = _server_key()
    result, fake_client = _run_ping(monkeypatch, captured=server_key, known=None)
    assert result.host_key.first_seen is True
    assert result.host_key.key_b64 == server_key.get_base64()
    assert result.host_key.fingerprint == server_key.fingerprint
    assert result.docker_version == "27.0.1"
    assert fake_client.closed is True


def test_recorded_key_verified_without_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    server_key = _server_key()
    known = KnownHostKey(key_type=server_key.get_name(), key_b64=server_key.get_base64())
    result, _ = _run_ping(monkeypatch, captured=None, known=known)
    assert result.host_key.first_seen is False
    assert result.host_key.fingerprint == server_key.fingerprint


def test_captured_key_mismatching_recorded_key_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded = _server_key()
    different = _server_key()
    known = KnownHostKey(key_type=recorded.get_name(), key_b64=recorded.get_base64())
    with pytest.raises(HostKeyMismatchError):
        _run_ping(monkeypatch, captured=different, known=known)


def test_auth_failure_maps_to_ssh_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_build(**kwargs: Any) -> Any:
        raise paramiko.AuthenticationException("denied")

    monkeypatch.setattr(docker_service, "build_docker_client", fake_build)
    with pytest.raises(SSHAuthError):
        docker_service._ping_blocking(
            address="203.0.113.10",
            port=22,
            username="docker",
            private_key_pem=_pkey_pem(),
            known_host_key=None,
        )
