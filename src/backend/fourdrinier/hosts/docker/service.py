"""Docker host operations: connect over SSH, ping, record TOFU host key."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

import docker.errors
import paramiko
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.crypto import decrypt_secret
from fourdrinier.core.settings import Settings
from fourdrinier.db.models import DockerHost
from fourdrinier.hosts.docker.client import KnownHostKey, build_docker_client
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    HostUnreachableError,
    SSHAuthError,
)
from fourdrinier.hosts.docker.types import ObservedHostKey
from fourdrinier.hosts.ssh.keys import load_pkey


@dataclass(frozen=True)
class PingResult:
    """Outcome of a successful host ping."""

    latency_ms: float
    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: ObservedHostKey


def _ping_blocking(
    *,
    address: str,
    port: int,
    username: str,
    private_key_pem: str,
    known_host_key: KnownHostKey | None,
) -> PingResult:
    pkey: paramiko.PKey = load_pkey(private_key_pem)
    client = None
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
            raise HostUnreachableError(f"could not reach {address}:{port}: {exc}") from exc

        captured: paramiko.PKey | None = adapter.captured_host_key
        if known_host_key is not None and captured is not None:
            # Recorded key existed but paramiko fell through to the missing-key
            # policy (entry-name drift, e.g. a port change). Compare manually.
            if captured.get_base64() != known_host_key.key_b64:
                raise HostKeyMismatchError(
                    f"host key for {address!r} does not match the recorded key; "
                    "possible man-in-the-middle or host reinstall"
                )

        try:
            client.ping()
            version_info: dict[str, object] = client.version()
        except docker.errors.DockerException as exc:
            raise HostUnreachableError(
                f"SSH connection to {address!r} succeeded but the Docker "
                f"daemon did not respond: {exc}"
            ) from exc
        latency_ms: float = (perf_counter() - started) * 1000

        if captured is not None:
            observed = ObservedHostKey(
                key_type=captured.get_name(),
                key_b64=captured.get_base64(),
                fingerprint=captured.fingerprint,
                first_seen=known_host_key is None,
            )
        else:
            assert known_host_key is not None  # preloaded key verified by paramiko
            recorded_pkey: paramiko.PKey = known_host_key.to_pkey(address)
            observed = ObservedHostKey(
                key_type=known_host_key.key_type,
                key_b64=known_host_key.key_b64,
                fingerprint=recorded_pkey.fingerprint,
                first_seen=False,
            )

        return PingResult(
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


async def ping_host(
    session: AsyncSession, host: DockerHost, settings: Settings | None = None
) -> PingResult:
    """Ping ``host`` over SSH and persist TOFU host key + last_seen_at.

    Raises:
        SSHAuthError: SSH rejected the keypair.
        HostUnreachableError: host or Docker daemon unreachable.
        HostKeyMismatchError: presented host key differs from the recorded one.
        DecryptionError / EncryptionKeyError: stored key cannot be decrypted.
    """
    private_key_pem: str = decrypt_secret(host.keypair.private_key_encrypted, settings).decode()
    known_host_key: KnownHostKey | None = None
    if host.host_key_type and host.host_key_b64:
        known_host_key = KnownHostKey(key_type=host.host_key_type, key_b64=host.host_key_b64)

    # docker-py and paramiko are blocking; keep the event loop free.
    result: PingResult = await asyncio.to_thread(
        _ping_blocking,
        address=host.address,
        port=host.port,
        username=host.username,
        private_key_pem=private_key_pem,
        known_host_key=known_host_key,
    )

    host.host_key_type = result.host_key.key_type
    host.host_key_b64 = result.host_key.key_b64
    host.host_key_fingerprint = result.host_key.fingerprint
    host.last_seen_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(host)
    return result


__all__ = ["ObservedHostKey", "PingResult", "ping_host"]
