"""
test_docker_driver.py

Unit tests for DockerHostDriver.ping.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from typing import Any, cast
from unittest.mock import Mock

import pytest

from fourdrinier.core.secrets import EncryptedSecret, PlaintextSecret, SecretDecryptor
from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KeypairSource,
    SSHKeypair,
)
from fourdrinier.hosts import (
    HostAuthenticationError,
    HostProviderMismatchError,
    HostTrustVerificationError,
    HostType,
    HostUnreachableError,
)
from fourdrinier.hosts.docker import (
    DockerHostDriver,
    DockerHostPingResult,
    ObservedHostKey,
)
from fourdrinier.hosts.docker import service as docker_service
from fourdrinier.hosts.docker.client import KnownHostKey
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    SSHAuthError,
)
from fourdrinier.hosts.docker.errors import (
    HostUnreachableError as DockerHostUnreachableError,
)

_HOST_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000301")
_KEYPAIR_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000302")
_HOST_KEY: ObservedHostKey = ObservedHostKey(
    key_type="ssh-ed25519",
    key_b64="AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKey",
    fingerprint="SHA256:fake-fingerprint",
    first_seen=True,
)
_REMOTE_RESULT: docker_service.PingResult = docker_service.PingResult(
    latency_ms=12.3,
    docker_version="27.0.1",
    api_version="1.41",
    os="linux",
    arch="amd64",
    host_key=_HOST_KEY,
)


def _docker_host() -> Host:
    keypair: SSHKeypair = SSHKeypair(
        id=_KEYPAIR_ID,
        name="production",
        source=KeypairSource.GENERATED,
        algorithm="ed25519",
        public_key="ssh-ed25519 AAAA public",
        fingerprint="SHA256:keypair",
        private_key_encrypted=b"ciphertext",
    )
    host: Host = Host(
        id=_HOST_ID,
        type=HostType.DOCKER,
        name="production",
        docker_details=DockerHostDetails(
            address="203.0.113.10",
            port=22,
            username="docker",
            keypair=keypair,
        ),
    )
    return host


async def test_docker_host_driver_ping_001_anomalous_host_type_does_not_match() -> None:
    """Test 001 - Anomalous
    Condition: The Docker driver receives a Kubernetes host
    Result: HostProviderMismatchError is raised before any remote operation
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = Host(type=HostType.KUBERNETES, name="production")

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="the Docker driver cannot operate on a kubernetes host",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.DOCKER
    decryptor.decrypt.assert_not_called()


async def test_docker_host_driver_ping_002_nominal_daemon_is_observed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 002 - Nominal
    Condition: The SSH key decrypts and an untrusted host responds to the Docker checks
    Result: Docker observations and first-seen host-key state are returned and attached
    """
    # Arrange
    captured: dict[str, Any] = {}

    def ping_blocking(**kwargs: Any) -> docker_service.PingResult:
        captured.update(kwargs)
        return _REMOTE_RESULT

    monkeypatch.setattr(docker_service, "_ping_blocking", ping_blocking)
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"private-key-pem")
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _docker_host()

    # Act
    result: DockerHostPingResult = await driver.ping(host)

    # Assert
    assert result.host_id == _HOST_ID
    assert result.type is HostType.DOCKER
    assert result.latency_ms == _REMOTE_RESULT.latency_ms
    assert result.observed_at.tzinfo is UTC
    assert result.docker_version == _REMOTE_RESULT.docker_version
    assert result.api_version == _REMOTE_RESULT.api_version
    assert result.os == _REMOTE_RESULT.os
    assert result.arch == _REMOTE_RESULT.arch
    assert result.host_key is _HOST_KEY
    assert host.docker_details is not None
    assert host.docker_details.host_key_type == _HOST_KEY.key_type
    assert host.docker_details.host_key_b64 == _HOST_KEY.key_b64
    assert host.docker_details.host_key_fingerprint == _HOST_KEY.fingerprint
    decryptor.decrypt.assert_called_once_with(EncryptedSecret(b"ciphertext"))
    assert captured == {
        "address": "203.0.113.10",
        "port": 22,
        "username": "docker",
        "private_key_pem": "private-key-pem",
        "known_host_key": None,
    }


async def test_docker_host_driver_ping_003_anomalous_details_are_missing() -> None:
    """Test 003 - Anomalous
    Condition: A Docker host aggregate has no Docker details loaded
    Result: HostProviderMismatchError identifies the malformed Docker aggregate
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = Host(id=_HOST_ID, type=HostType.DOCKER, name="production")

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="the Docker host has no Docker details",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.DOCKER
    decryptor.decrypt.assert_not_called()


async def test_docker_host_driver_ping_004_anomalous_keypair_is_missing() -> None:
    """Test 004 - Anomalous
    Condition: A Docker host aggregate has details without an SSH keypair
    Result: HostProviderMismatchError identifies the incomplete Docker aggregate
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _docker_host()
    assert host.docker_details is not None
    host.docker_details.keypair = None  # type: ignore[assignment]

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="the Docker host has no SSH keypair",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.DOCKER
    decryptor.decrypt.assert_not_called()


async def test_docker_host_driver_ping_005_anomalous_private_key_is_not_utf8() -> None:
    """Test 005 - Anomalous
    Condition: The decrypted SSH private key is not valid UTF-8
    Result: HostAuthenticationError is raised before contacting the Docker host
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"\xff")
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))

    # Act
    with pytest.raises(
        HostAuthenticationError,
        match="the stored Docker SSH private key is not valid UTF-8",
    ) as captured:
        await driver.ping(_docker_host())

    # Assert
    assert captured.value.provider is HostType.DOCKER
    assert isinstance(captured.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    ("key_type", "key_b64"),
    [
        pytest.param("ssh-ed25519", None, id="missing-material"),
        pytest.param(None, "AAAA recorded", id="missing-type"),
    ],
)
async def test_docker_host_driver_ping_006_anomalous_recorded_host_key_is_incomplete(
    key_type: str | None,
    key_b64: str | None,
) -> None:
    """Test 006 - Anomalous
    Condition: Only one required part of the recorded SSH host key is present
    Result: HostTrustVerificationError prevents an unverified connection attempt
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"private-key-pem")
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _docker_host()
    assert host.docker_details is not None
    host.docker_details.host_key_type = key_type
    host.docker_details.host_key_b64 = key_b64

    # Act
    with pytest.raises(
        HostTrustVerificationError,
        match="the recorded Docker SSH host key is incomplete",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.DOCKER


async def test_docker_host_driver_ping_007_nominal_recorded_host_key_is_reused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 007 - Nominal
    Condition: Complete SSH host-key trust state was recorded by an earlier ping
    Result: The exact key is supplied for verification during the next connection
    """
    # Arrange
    captured: dict[str, Any] = {}

    def ping_blocking(**kwargs: Any) -> docker_service.PingResult:
        captured.update(kwargs)
        return _REMOTE_RESULT

    monkeypatch.setattr(docker_service, "_ping_blocking", ping_blocking)
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"private-key-pem")
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _docker_host()
    assert host.docker_details is not None
    host.docker_details.host_key_type = "ssh-ed25519"
    host.docker_details.host_key_b64 = "AAAA recorded"

    # Act
    await driver.ping(host)

    # Assert
    assert captured["known_host_key"] == KnownHostKey(
        key_type="ssh-ed25519",
        key_b64="AAAA recorded",
    )


@pytest.mark.parametrize(
    ("provider_error", "domain_error"),
    [
        pytest.param(
            SSHAuthError("auth rejected"),
            HostAuthenticationError,
            id="authentication",
        ),
        pytest.param(
            HostKeyMismatchError("host key changed"),
            HostTrustVerificationError,
            id="trust",
        ),
        pytest.param(
            DockerHostUnreachableError("no route"),
            HostUnreachableError,
            id="unreachable",
        ),
    ],
)
async def test_docker_host_driver_ping_008_anomalous_provider_failure_is_translated(
    monkeypatch: pytest.MonkeyPatch,
    provider_error: Exception,
    domain_error: type[Exception],
) -> None:
    """Test 008 - Anomalous
    Condition: The Docker ping boundary reports a typed provider failure
    Result: The matching stable host-domain error preserves the message and cause
    """

    # Arrange
    def ping_blocking(**_kwargs: Any) -> docker_service.PingResult:
        raise provider_error

    monkeypatch.setattr(docker_service, "_ping_blocking", ping_blocking)
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"private-key-pem")
    driver: DockerHostDriver = DockerHostDriver(cast(SecretDecryptor, decryptor))

    # Act
    with pytest.raises(domain_error, match=str(provider_error)) as captured:
        await driver.ping(_docker_host())

    # Assert
    assert captured.value.__cause__ is provider_error
    assert captured.value.provider is HostType.DOCKER
