"""
types.py

Define Docker-specific host operation result types.
"""

from __future__ import annotations

from dataclasses import dataclass

from fourdrinier.hosts.types import HostPingResult


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservedHostKey:
    """Describe SSH host key material observed or verified during a connection."""

    key_type: str
    key_b64: str
    fingerprint: str
    first_seen: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class DockerHostPingResult(HostPingResult):
    """Include Docker and SSH observations with a provider-neutral ping result."""

    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: ObservedHostKey


__all__: list[str] = ["DockerHostPingResult", "ObservedHostKey"]
