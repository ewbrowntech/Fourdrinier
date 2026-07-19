"""
deployment.py

Define provider-neutral container deployment specifications for Minecraft runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NetworkProtocol(StrEnum):
    """Network transports exposed by a runtime deployment."""

    TCP = "tcp"
    UDP = "udp"


@dataclass(frozen=True, slots=True)
class ContainerPort:
    """Describe a named port exposed by a runtime container."""

    name: str
    container_port: int
    protocol: NetworkProtocol


@dataclass(frozen=True, slots=True)
class EnvironmentVariable:
    """Describe an environment variable supplied to a runtime container."""

    name: str
    value: str


@dataclass(frozen=True, slots=True)
class PersistentMount:
    """Describe provider-managed persistent storage mounted into a container."""

    name: str
    container_path: str


@dataclass(frozen=True, slots=True)
class GeneratedFile:
    """Describe a generated file written relative to a persistent mount."""

    mount_name: str
    relative_path: str
    content: str
    mode: int


@dataclass(frozen=True, slots=True)
class ResourceAllocation:
    """Describe the CPU and memory assigned to one server deployment."""

    cpu_millicores: int
    memory_bytes: int


@dataclass(frozen=True, slots=True)
class TcpHealthCheck:
    """Describe a TCP readiness probe for a runtime container."""

    port: int
    initial_delay_seconds: int
    period_seconds: int
    timeout_seconds: int
    failure_threshold: int


@dataclass(frozen=True, slots=True)
class DeploymentSpec:
    """Describe a runtime deployment without provider-specific workload types.

    The command is the complete process invocation and replaces image process defaults when a
    host driver constructs its provider workload.
    """

    image_reference: str
    command: tuple[str, ...]
    env: tuple[EnvironmentVariable, ...]
    persistent_mounts: tuple[PersistentMount, ...]
    ports: tuple[ContainerPort, ...]
    resources: ResourceAllocation
    generated_files: tuple[GeneratedFile, ...]
    health_check: TcpHealthCheck


__all__: list[str] = [
    "ContainerPort",
    "DeploymentSpec",
    "EnvironmentVariable",
    "GeneratedFile",
    "NetworkProtocol",
    "PersistentMount",
    "ResourceAllocation",
    "TcpHealthCheck",
]
