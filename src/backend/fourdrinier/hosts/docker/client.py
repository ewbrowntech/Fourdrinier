"""Docker SDK client over SSH with injected in-memory credentials.

docker-py's ``SSHHTTPAdapter`` only reads ``~/.ssh/config`` and the agent for
credentials (docker/docker-py#2416), so this module subclasses it to inject a
paramiko ``PKey`` directly — the private key never touches disk — and to
control host-key verification (trust-on-first-use, see ``operations/ping.py``).

This rides on docker-py internals (``_create_paramiko_client``/``ssh_params``
and the ``http+docker://ssh`` mount in ``APIClient``); the dependency is pinned
to ``docker>=7.1,<8`` in pyproject.toml — re-verify on upgrade.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

import docker
import paramiko
from docker.transport import SSHHTTPAdapter

# Docker API version floor; pinned so APIClient skips eager auto-negotiation
# over SSH before our adapter is mounted. 1.41 == Docker Engine 20.10+.
DOCKER_API_VERSION = "1.41"

DEFAULT_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class KnownHostKey:
    """A previously recorded SSH host key (exact key, not just fingerprint)."""

    key_type: str
    key_b64: str

    def to_pkey(self, hostname: str) -> paramiko.PKey:
        entry = paramiko.hostkeys.HostKeyEntry.from_line(
            f"{hostname} {self.key_type} {self.key_b64}"
        )
        if entry is None or entry.key is None:
            raise ValueError(f"recorded host key for {hostname!r} is unparseable")
        return entry.key


class _CaptureHostKeyPolicy(paramiko.MissingHostKeyPolicy):
    """Accept unknown host keys and hand them to the adapter for recording.

    Verification against a previously recorded key happens in two places:
    paramiko raises ``BadHostKeyException`` when the recorded entry exists
    under the exact host-key name, and the service compares any captured key
    against the recorded one after connecting (covers entry-name drift).
    """

    def __init__(self, sink: list[paramiko.PKey]) -> None:
        self._sink = sink

    def missing_host_key(
        self, client: paramiko.SSHClient, hostname: str, key: paramiko.PKey
    ) -> None:
        self._sink.append(key)


def host_key_entry_name(hostname: str, port: int) -> str:
    """The known_hosts entry name paramiko looks up for a host/port pair."""
    return hostname if port == 22 else f"[{hostname}]:{port}"


class SSHDockerAdapter(SSHHTTPAdapter):
    """SSHHTTPAdapter with an explicit private key and host-key policy.

    Unlike the parent class this never consults ``~/.ssh/config``, the SSH
    agent, or on-disk keys — connections are fully determined by what the
    application passes in.
    """

    def __init__(
        self,
        base_url: str,
        *,
        pkey: paramiko.PKey,
        known_host_key: KnownHostKey | None = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._pkey = pkey
        self._known_host_key = known_host_key
        self._connect_timeout = timeout
        self._captured_keys: list[paramiko.PKey] = []
        # super().__init__ invokes _create_paramiko_client + _connect, so the
        # attributes above must exist first.
        super().__init__(base_url, timeout=timeout)

    @property
    def captured_host_key(self) -> paramiko.PKey | None:
        """Host key offered by the server when none was preloaded."""
        return self._captured_keys[-1] if self._captured_keys else None

    def _create_paramiko_client(self, base_url: str) -> None:
        parsed = urllib.parse.urlparse(base_url)
        if not parsed.hostname:
            raise ValueError(f"invalid docker ssh URL: {base_url!r}")
        port: int = parsed.port or 22

        self.ssh_client = paramiko.SSHClient()
        self.ssh_params = {
            "hostname": parsed.hostname,
            "port": port,
            "username": parsed.username,
            "pkey": self._pkey,
            "allow_agent": False,
            "look_for_keys": False,
            "timeout": self._connect_timeout,
        }

        if self._known_host_key is not None:
            entry_name: str = host_key_entry_name(parsed.hostname, port)
            self.ssh_client.get_host_keys().add(
                entry_name,
                self._known_host_key.key_type,
                self._known_host_key.to_pkey(entry_name),
            )
        self.ssh_client.set_missing_host_key_policy(_CaptureHostKeyPolicy(self._captured_keys))


def build_docker_client(
    *,
    address: str,
    port: int,
    username: str,
    pkey: paramiko.PKey,
    known_host_key: KnownHostKey | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[docker.APIClient, SSHDockerAdapter]:
    """Connect to a remote Docker daemon over SSH.

    Returns the API client plus the adapter (for the captured host key).
    Raises paramiko exceptions on SSH failure; the caller maps them.
    """
    base_url: str = f"ssh://{urllib.parse.quote(username)}@{address}:{port}"
    # The adapter connects eagerly — do the risky part first.
    adapter = SSHDockerAdapter(base_url, pkey=pkey, known_host_key=known_host_key, timeout=timeout)
    # use_ssh_client=True makes APIClient build its lazy shell-out adapter (no
    # connection at init); we immediately replace it with ours. A fixed API
    # version prevents eager version auto-negotiation before the swap.
    client = docker.APIClient(
        base_url=base_url,
        version=DOCKER_API_VERSION,
        timeout=timeout,
        use_ssh_client=True,
    )
    stub_adapter = client._custom_adapter
    client._custom_adapter = adapter
    client.mount("http+docker://ssh", adapter)
    stub_adapter.close()
    return client, adapter


__all__ = [
    "DOCKER_API_VERSION",
    "KnownHostKey",
    "SSHDockerAdapter",
    "build_docker_client",
    "host_key_entry_name",
]
