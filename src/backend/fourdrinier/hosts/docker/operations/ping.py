"""
ping.py

Check Docker daemon connectivity over SSH and maintain host-key trust state.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

import docker
import paramiko

from fourdrinier.core.secrets import EncryptedSecret, SecretDecryptor
from fourdrinier.db.models import DockerHostDetails, Host, SSHKeypair
from fourdrinier.hosts.docker.client import KnownHostKey, SSHDockerAdapter, build_docker_client
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    SSHAuthError,
)
from fourdrinier.hosts.docker.errors import (
    HostUnreachableError as DockerHostUnreachableError,
)
from fourdrinier.hosts.docker.types import DockerHostPingResult, ObservedHostKey
from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostProviderMismatchError,
    HostTrustVerificationError,
    HostUnreachableError,
)
from fourdrinier.hosts.ssh.keys import load_pkey
from fourdrinier.hosts.types import HostType


@dataclass(frozen=True, slots=True)
class DockerPingObservation:
    """Represent raw observations from a successful Docker connectivity check."""

    latency_ms: float
    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: ObservedHostKey


def _known_host_key(details: DockerHostDetails) -> KnownHostKey | None:
    key_type_present: bool = details.host_key_type is not None
    key_material_present: bool = details.host_key_b64 is not None
    if key_type_present is not key_material_present:
        raise HostTrustVerificationError(
            "the recorded Docker SSH host key is incomplete",
            provider=HostType.DOCKER,
        )
    if details.host_key_type is None or details.host_key_b64 is None:
        return None
    known_host_key: KnownHostKey = KnownHostKey(
        key_type=details.host_key_type,
        key_b64=details.host_key_b64,
    )
    return known_host_key


def _ping_remote(
    *,
    address: str,
    port: int,
    username: str,
    private_key_pem: str,
    known_host_key: KnownHostKey | None,
) -> DockerPingObservation:
    pkey: paramiko.PKey = load_pkey(private_key_pem)
    client: docker.APIClient | None = None
    adapter: SSHDockerAdapter
    try:
        started: float = perf_counter()
        try:
            client, adapter = build_docker_client(
                address=address,
                port=port,
                username=username,
                pkey=pkey,
                known_host_key=known_host_key,
            )
        except paramiko.BadHostKeyException as exc:
            raise HostKeyMismatchError(
                f"host key for {address!r} does not match the recorded key; "
                "possible man-in-the-middle or host reinstall"
            ) from exc
        except paramiko.AuthenticationException as exc:
            raise SSHAuthError(f"SSH authentication failed for {username}@{address}") from exc
        except (paramiko.SSHException, OSError, TimeoutError) as exc:
            raise DockerHostUnreachableError(f"could not reach {address}:{port}: {exc}") from exc

        captured: paramiko.PKey | None = adapter.captured_host_key
        if (
            known_host_key is not None
            and captured is not None
            and captured.get_base64() != known_host_key.key_b64
        ):
            raise HostKeyMismatchError(
                f"host key for {address!r} does not match the recorded key; "
                "possible man-in-the-middle or host reinstall"
            )

        try:
            client.ping()
            version_info: dict[str, object] = client.version()
        except docker.errors.DockerException as exc:
            raise DockerHostUnreachableError(
                f"SSH connection to {address!r} succeeded but the Docker "
                f"daemon did not respond: {exc}"
            ) from exc
        latency_ms: float = (perf_counter() - started) * 1000

        if captured is not None:
            observed: ObservedHostKey = ObservedHostKey(
                key_type=captured.get_name(),
                key_b64=captured.get_base64(),
                fingerprint=captured.fingerprint,
                first_seen=known_host_key is None,
            )
        else:
            assert known_host_key is not None
            recorded_pkey: paramiko.PKey = known_host_key.to_pkey(address)
            observed = ObservedHostKey(
                key_type=known_host_key.key_type,
                key_b64=known_host_key.key_b64,
                fingerprint=recorded_pkey.fingerprint,
                first_seen=False,
            )

        return DockerPingObservation(
            latency_ms=round(latency_ms, 1),
            docker_version=str(version_info.get("Version", "")),
            api_version=str(version_info.get("ApiVersion", "")),
            os=str(version_info.get("Os", "")),
            arch=str(version_info.get("Arch", "")),
            host_key=observed,
        )
    finally:
        if client is not None:
            client.close()


async def ping(host: Host, secret_decryptor: SecretDecryptor) -> DockerHostPingResult:
    """Check a Docker host over SSH and update its host-key trust state.

    Args:
        host: Host aggregate with Docker details and its SSH keypair loaded.
        secret_decryptor: Decryptor for the stored SSH private key.

    Returns:
        Shared and Docker-specific observations from the remote daemon.

    Raises:
        HostProviderMismatchError: If the host is not a complete Docker aggregate.
        SecretError: If the stored private key cannot be decrypted.
        HostAuthenticationError: If SSH rejects the configured private key.
        HostTrustVerificationError: If SSH host-key verification fails.
        HostUnreachableError: If SSH or the Docker daemon cannot be reached.
    """
    if host.type is not HostType.DOCKER:
        raise HostProviderMismatchError(
            f"the Docker driver cannot operate on a {host.type.value} host",
            provider=HostType.DOCKER,
        )
    details: DockerHostDetails | None = host.docker_details
    if details is None:
        raise HostProviderMismatchError(
            "the Docker host has no Docker details",
            provider=HostType.DOCKER,
        )
    keypair: SSHKeypair | None = details.keypair
    if keypair is None:
        raise HostProviderMismatchError(
            "the Docker host has no SSH keypair",
            provider=HostType.DOCKER,
        )

    private_key_bytes: bytes = secret_decryptor.decrypt(
        EncryptedSecret(keypair.private_key_encrypted)
    )
    try:
        private_key_pem: str = private_key_bytes.decode()
    except UnicodeDecodeError as exc:
        raise HostAuthenticationError(
            "the stored Docker SSH private key is not valid UTF-8",
            provider=HostType.DOCKER,
        ) from exc

    known_host_key: KnownHostKey | None = _known_host_key(details)
    try:
        result: DockerPingObservation = await asyncio.to_thread(
            _ping_remote,
            address=details.address,
            port=details.port,
            username=details.username,
            private_key_pem=private_key_pem,
            known_host_key=known_host_key,
        )
    except SSHAuthError as exc:
        raise HostAuthenticationError(str(exc), provider=HostType.DOCKER) from exc
    except HostKeyMismatchError as exc:
        raise HostTrustVerificationError(str(exc), provider=HostType.DOCKER) from exc
    except DockerHostUnreachableError as exc:
        raise HostUnreachableError(str(exc), provider=HostType.DOCKER) from exc

    details.host_key_type = result.host_key.key_type
    details.host_key_b64 = result.host_key.key_b64
    details.host_key_fingerprint = result.host_key.fingerprint
    return DockerHostPingResult(
        host_id=host.id,
        type=HostType.DOCKER,
        latency_ms=result.latency_ms,
        observed_at=datetime.now(UTC),
        docker_version=result.docker_version,
        api_version=result.api_version,
        os=result.os,
        arch=result.arch,
        host_key=result.host_key,
    )


__all__: list[str] = ["ping"]
