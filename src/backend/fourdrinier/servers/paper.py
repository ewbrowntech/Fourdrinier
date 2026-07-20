"""
paper.py

Translate Paper logical servers into itzg/minecraft-server deployment specifications.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import httpx

from fourdrinier.servers.deployment import (
    ContainerPort,
    DeploymentSpec,
    EnvironmentVariable,
    NetworkProtocol,
    PersistentMount,
    ResourceAllocation,
    TcpHealthCheck,
)
from fourdrinier.servers.errors import (
    RuntimeVersionSourceError,
    ServerVersionUnsupportedError,
)
from fourdrinier.servers.types import ServerRuntime

if TYPE_CHECKING:
    from fourdrinier.db.models import Server

PAPER_FILL_PROJECT_URL: str = "https://fill.papermc.io/v3/projects/paper"
# Fill rejects generic User-Agent values; identify Fourdrinier with a contact URL.
PAPER_FILL_USER_AGENT: str = "fourdrinier/0.1.0 (https://github.com/ewbrowntech/fourdrinier)"
PAPER_FILL_TIMEOUT_SECONDS: float = 10.0
PAPER_MINIMUM_CPU_MILLICORES: int = 1_000
PAPER_MINIMUM_MEMORY_BYTES: int = 2 * 1024 * 1024 * 1024
PAPER_IMAGE_REPOSITORY: str = "itzg/minecraft-server"
PAPER_DATA_MOUNT_NAME: str = "data"
PAPER_DATA_PATH: str = "/data"
PAPER_PORT: int = 25565
# Reserve headroom below the container limit for JVM overhead beyond the heap.
PAPER_MEMORY_OVERHEAD_BYTES: int = 512 * 1024 * 1024
# Paper recommended Java floors (docs.papermc.io/paper/getting-started), newest first.
# Tags match Hub's Java variants (itzg/minecraft-server:java25, :java21, …).
PAPER_JAVA_IMAGE_TAGS: tuple[tuple[tuple[int, ...], str], ...] = (
    ((26, 1), "java25"),
    ((1, 20), "java21"),
    ((1, 17), "java17"),
    ((1, 16, 5), "java16"),
    ((1, 12), "java11"),
)
PAPER_FALLBACK_JAVA_IMAGE_TAG: str = "java8"


def _version_ordinal(version: str) -> tuple[int, ...]:
    """Parse a dotted Minecraft version into a comparable integer tuple.

    Args:
        version: Dotted Minecraft version, such as "1.20.5", "26.2", or a
            pre-release form like "1.13-pre7".

    Returns:
        The leading numeric components of the version, in order. Parsing stops
        at the first component without a leading integer, so pre-release
        suffixes never fail translation.
    """
    components: list[int] = []
    for component in version.split("."):
        digits_match: re.Match[str] | None = re.match(r"\d+", component)
        if digits_match is None:
            break
        components.append(int(digits_match.group()))
    return tuple(components)


def _image_reference(minecraft_version: str) -> str:
    """Select the itzg Java image variant for Paper's recommended JVM.

    Args:
        minecraft_version: Concrete Minecraft version being deployed.

    Returns:
        An itzg/minecraft-server image reference tagged by Java variant.
    """
    ordinal: tuple[int, ...] = _version_ordinal(minecraft_version)
    java_tag: str = PAPER_FALLBACK_JAVA_IMAGE_TAG
    for minimum, tag in PAPER_JAVA_IMAGE_TAGS:
        if ordinal >= minimum:
            java_tag = tag
            break
    return f"{PAPER_IMAGE_REPOSITORY}:{java_tag}"


def _heap_megabytes(memory_bytes: int) -> int:
    """Derive the JVM heap size from the container memory allocation.

    Args:
        memory_bytes: Container memory allocation in bytes.

    Returns:
        The heap size in mebibytes, leaving overhead below the container limit.
    """
    heap_bytes: int = memory_bytes - PAPER_MEMORY_OVERHEAD_BYTES
    return heap_bytes // (1024 * 1024)


class PaperRuntime:
    """Build deployment specifications for Paper on the itzg/minecraft-server image."""

    runtime: ServerRuntime = ServerRuntime.PAPER
    minimum_resources: ResourceAllocation = ResourceAllocation(
        cpu_millicores=PAPER_MINIMUM_CPU_MILLICORES,
        memory_bytes=PAPER_MINIMUM_MEMORY_BYTES,
    )

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialize the adapter with an optional HTTP transport override.

        Args:
            transport: Transport handling Fill API requests; primarily an
                injection point for tests (httpx.MockTransport).
        """
        self._transport: httpx.AsyncBaseTransport | None = transport

    async def _fetch_versions(self) -> list[str]:
        """Fetch the Minecraft versions Paper publishes builds for.

        Returns:
            Minecraft versions from the Fill API, newest first.

        Raises:
            RuntimeVersionSourceError: If the Fill API is unreachable, rejects the
                request, or returns an unexpected payload.
        """
        headers: dict[str, str] = {"User-Agent": PAPER_FILL_USER_AGENT}
        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=PAPER_FILL_TIMEOUT_SECONDS,
                transport=self._transport,
            ) as client:
                response: httpx.Response = await client.get(PAPER_FILL_PROJECT_URL)
                response.raise_for_status()
                payload: Any = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeVersionSourceError(
                f"failed to fetch Paper versions from {PAPER_FILL_PROJECT_URL}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise RuntimeVersionSourceError(
                f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}"
            ) from exc
        families: Any = payload.get("versions") if isinstance(payload, dict) else None
        if not isinstance(families, dict):
            raise RuntimeVersionSourceError(
                f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}"
            )
        versions: list[str] = []
        for family_versions in families.values():
            if not isinstance(family_versions, list):
                raise RuntimeVersionSourceError(
                    f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}"
                )
            versions.extend(str(version) for version in family_versions)
        if not versions:
            raise RuntimeVersionSourceError(
                f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}"
            )
        return versions

    async def resolve_version(self, requested: str | None) -> str:
        """Resolve a requested Minecraft version against Paper's published versions.

        Args:
            requested: Minecraft version requested by the caller, or None for the
                latest version Paper publishes.

        Returns:
            The concrete Minecraft version Paper will deploy.

        Raises:
            ServerVersionUnsupportedError: If Paper publishes no build for the
                requested version.
            RuntimeVersionSourceError: If the Fill API cannot be consulted.
        """
        versions: list[str] = await self._fetch_versions()
        if requested is None:
            return versions[0]
        if requested in versions:
            return requested
        raise ServerVersionUnsupportedError(
            f"paper does not support Minecraft version {requested!r}"
        )

    async def list_versions(self) -> list[str]:
        """List the Minecraft versions Paper publishes builds for.

        Returns:
            Minecraft versions from the Fill API, newest first.

        Raises:
            RuntimeVersionSourceError: If the Fill API cannot be consulted.
        """
        versions: list[str] = await self._fetch_versions()
        return versions

    def deployment_spec(self, server: Server) -> DeploymentSpec:
        """Build an itzg/minecraft-server deployment specification for Paper.

        Args:
            server: Logical Paper server being translated.

        Returns:
            A provider-neutral specification driving the itzg image via env vars.
        """
        specification: DeploymentSpec = DeploymentSpec(
            image_reference=_image_reference(server.minecraft_version),
            env=(
                EnvironmentVariable(name="TYPE", value="PAPER"),
                EnvironmentVariable(name="VERSION", value=server.minecraft_version),
                # Deploying a Paper server implies the operator accepts the
                # Minecraft EULA; the itzg image refuses to start without it.
                EnvironmentVariable(name="EULA", value="TRUE"),
                EnvironmentVariable(
                    name="MEMORY",
                    value=f"{_heap_megabytes(server.memory_bytes)}M",
                ),
            ),
            persistent_mounts=(
                PersistentMount(
                    name=PAPER_DATA_MOUNT_NAME,
                    container_path=PAPER_DATA_PATH,
                ),
            ),
            ports=(
                ContainerPort(
                    name="minecraft",
                    container_port=PAPER_PORT,
                    protocol=NetworkProtocol.TCP,
                ),
            ),
            resources=ResourceAllocation(
                cpu_millicores=server.cpu_millicores,
                memory_bytes=server.memory_bytes,
            ),
            # itzg manages server.properties itself; no generated files.
            generated_files=(),
            # First boot downloads the Paper jar and generates the world.
            health_check=TcpHealthCheck(
                port=PAPER_PORT,
                initial_delay_seconds=120,
                period_seconds=30,
                timeout_seconds=30,
                failure_threshold=3,
            ),
        )
        return specification


__all__: list[str] = [
    "PAPER_DATA_MOUNT_NAME",
    "PAPER_DATA_PATH",
    "PAPER_FALLBACK_JAVA_IMAGE_TAG",
    "PAPER_FILL_PROJECT_URL",
    "PAPER_FILL_TIMEOUT_SECONDS",
    "PAPER_FILL_USER_AGENT",
    "PAPER_IMAGE_REPOSITORY",
    "PAPER_JAVA_IMAGE_TAGS",
    "PAPER_MEMORY_OVERHEAD_BYTES",
    "PAPER_MINIMUM_CPU_MILLICORES",
    "PAPER_MINIMUM_MEMORY_BYTES",
    "PAPER_PORT",
    "PaperRuntime",
]
