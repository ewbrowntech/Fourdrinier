"""
pumpkin.py

Translate Pumpkin logical servers into upstream container deployment specifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fourdrinier.servers.deployment import (
    ContainerPort,
    DeploymentSpec,
    GeneratedFile,
    NetworkProtocol,
    PersistentMount,
    ResourceAllocation,
    TcpHealthCheck,
)
from fourdrinier.servers.errors import ServerVersionUnsupportedError
from fourdrinier.servers.types import ServerRuntime

if TYPE_CHECKING:
    from fourdrinier.db.models import Server

PUMPKIN_MINECRAFT_VERSION: str = "26.2"
PUMPKIN_MINIMUM_CPU_MILLICORES: int = 2_000
PUMPKIN_MINIMUM_MEMORY_BYTES: int = 2 * 1024 * 1024 * 1024
PUMPKIN_IMAGE_REFERENCE: str = "ghcr.io/pumpkin-mc/pumpkin:latest"
PUMPKIN_DATA_MOUNT_NAME: str = "data"
PUMPKIN_DATA_PATH: str = "/pumpkin"
PUMPKIN_PORT: int = 25565
PUMPKIN_CONFIGURATION: str = """[networking.java]
enabled = true
address = "0.0.0.0:25565"
motd = "A Fourdrinier Pumpkin server!"
"""


class PumpkinRuntime:
    """Build deployment specifications for the official upstream Pumpkin image."""

    runtime: ServerRuntime = ServerRuntime.PUMPKIN
    minimum_resources: ResourceAllocation = ResourceAllocation(
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
    )

    def resolve_version(self, requested: str | None) -> str:
        """Resolve a requested Minecraft version to the single supported Pumpkin version.

        Args:
            requested: Minecraft version requested by the caller, or None for the
                current Pumpkin default.

        Returns:
            The pinned Minecraft version served by the upstream Pumpkin image.

        Raises:
            ServerVersionUnsupportedError: If the requested version is not the pinned
                Pumpkin version.
        """
        if requested is None or requested == PUMPKIN_MINECRAFT_VERSION:
            return PUMPKIN_MINECRAFT_VERSION
        raise ServerVersionUnsupportedError(
            f"pumpkin only supports Minecraft version {PUMPKIN_MINECRAFT_VERSION}"
        )

    async def list_versions(self) -> list[str]:
        """List the single Minecraft version served by the upstream Pumpkin image.

        Returns:
            A one-element list containing the pinned Pumpkin Minecraft version.
        """
        return [PUMPKIN_MINECRAFT_VERSION]

    def deployment_spec(self, server: Server) -> DeploymentSpec:
        """Build an upstream Pumpkin deployment specification.

        Args:
            server: Logical Pumpkin server being translated.

        Returns:
            A provider-neutral specification for the current Pumpkin runtime.
        """
        specification: DeploymentSpec = DeploymentSpec(
            image_reference=PUMPKIN_IMAGE_REFERENCE,
            command=("/bin/pumpkin",),
            env=(),
            persistent_mounts=(
                PersistentMount(
                    name=PUMPKIN_DATA_MOUNT_NAME,
                    container_path=PUMPKIN_DATA_PATH,
                ),
            ),
            ports=(
                ContainerPort(
                    name="minecraft",
                    container_port=PUMPKIN_PORT,
                    protocol=NetworkProtocol.TCP,
                ),
            ),
            resources=ResourceAllocation(
                cpu_millicores=server.cpu_millicores,
                memory_bytes=server.memory_bytes,
            ),
            generated_files=(
                GeneratedFile(
                    mount_name=PUMPKIN_DATA_MOUNT_NAME,
                    relative_path="pumpkin.toml",
                    content=PUMPKIN_CONFIGURATION,
                    mode=0o640,
                ),
            ),
            health_check=TcpHealthCheck(
                port=PUMPKIN_PORT,
                initial_delay_seconds=0,
                period_seconds=30,
                timeout_seconds=30,
                failure_threshold=3,
            ),
        )
        return specification


__all__: list[str] = [
    "PUMPKIN_CONFIGURATION",
    "PUMPKIN_DATA_MOUNT_NAME",
    "PUMPKIN_DATA_PATH",
    "PUMPKIN_IMAGE_REFERENCE",
    "PUMPKIN_MINECRAFT_VERSION",
    "PUMPKIN_MINIMUM_CPU_MILLICORES",
    "PUMPKIN_MINIMUM_MEMORY_BYTES",
    "PUMPKIN_PORT",
    "PumpkinRuntime",
]
