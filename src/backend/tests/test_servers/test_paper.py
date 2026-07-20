"""
test_paper.py

Unit tests for PaperRuntime version resolution and deployment translation.
"""

from __future__ import annotations

import json

import httpx
import pytest

from fourdrinier.db.models import Server
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
from fourdrinier.servers.paper import (
    PAPER_DATA_MOUNT_NAME,
    PAPER_DATA_PATH,
    PAPER_FILL_PROJECT_URL,
    PAPER_FILL_USER_AGENT,
    PAPER_IMAGE_REPOSITORY,
    PAPER_MINIMUM_CPU_MILLICORES,
    PAPER_MINIMUM_MEMORY_BYTES,
    PAPER_PORT,
    PaperRuntime,
)
from fourdrinier.servers.runtimes import RuntimeAdapter
from fourdrinier.servers.types import ServerRuntime

FILL_VERSIONS_PAYLOAD: dict[str, dict[str, list[str]]] = {
    "versions": {
        "26.2": ["26.2"],
        "26.1": ["26.1"],
        "1.21": ["1.21.4", "1.21.3"],
    },
}
FILL_VERSIONS_FLATTENED: list[str] = ["26.2", "26.1", "1.21.4", "1.21.3"]


def fill_runtime(
    payload: object = FILL_VERSIONS_PAYLOAD,
    status_code: int = 200,
) -> tuple[PaperRuntime, list[httpx.Request]]:
    """Build a Paper runtime whose Fill API transport returns a canned response.

    Args:
        payload: JSON body returned by the mocked Fill API, or raw response
            bytes when the body must not be JSON-encoded.
        status_code: HTTP status returned by the mocked Fill API.

    Returns:
        The runtime and the list collecting every request the runtime sends.
    """
    requests: list[httpx.Request] = []
    content: bytes = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, content=content)

    runtime: PaperRuntime = PaperRuntime(transport=httpx.MockTransport(respond))
    return runtime, requests


def test_paper_runtime_deployment_spec_001_nominal_logical_server_is_translated() -> None:
    """Test 001 - Nominal
    Condition: A logical Paper server is translated by the runtime adapter
    Result: The complete itzg-image deployment specification is provider-neutral
    """
    # Arrange
    runtime: PaperRuntime = PaperRuntime()
    server: Server = Server(
        name="paper-plains",
        runtime=ServerRuntime.PAPER,
        minecraft_version="1.21.4",
        cpu_millicores=2_750,
        memory_bytes=3_221_225_472,
    )
    expected: DeploymentSpec = DeploymentSpec(
        image_reference=f"{PAPER_IMAGE_REPOSITORY}:java21",
        env=(
            EnvironmentVariable(name="TYPE", value="PAPER"),
            EnvironmentVariable(name="VERSION", value="1.21.4"),
            EnvironmentVariable(name="EULA", value="TRUE"),
            EnvironmentVariable(name="MEMORY", value="2560M"),
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
        generated_files=(),
        health_check=TcpHealthCheck(
            port=PAPER_PORT,
            initial_delay_seconds=120,
            period_seconds=30,
            timeout_seconds=30,
            failure_threshold=3,
        ),
    )

    # Act
    result: DeploymentSpec = runtime.deployment_spec(server)

    # Assert
    assert result == expected
    assert runtime.runtime is ServerRuntime.PAPER
    assert runtime.minimum_resources == ResourceAllocation(
        cpu_millicores=PAPER_MINIMUM_CPU_MILLICORES,
        memory_bytes=PAPER_MINIMUM_MEMORY_BYTES,
    )
    assert isinstance(runtime, RuntimeAdapter)


@pytest.mark.parametrize(
    ("minecraft_version", "java_tag"),
    [
        pytest.param("1.8.8", "java8", id="legacy"),
        pytest.param("1.11.2", "java8", id="java8-ceiling"),
        pytest.param("1.RV-Pre1", "java8", id="non-numeric-component"),
        pytest.param("1.12", "java11", id="java11-floor"),
        pytest.param("1.13-pre7", "java11", id="pre-release-suffix"),
        pytest.param("1.16.4", "java11", id="java11-ceiling"),
        pytest.param("1.16.5", "java16", id="java16"),
        pytest.param("1.17.1", "java17", id="java17-floor"),
        pytest.param("1.19.4", "java17", id="java17-ceiling"),
        pytest.param("1.20", "java21", id="java21-floor"),
        pytest.param("1.20.4", "java21", id="java21-pre-vanilla-bump"),
        pytest.param("1.21.4", "java21", id="java21"),
        pytest.param("25.2", "java21", id="new-scheme-pre-java25"),
        pytest.param("26.1", "java25", id="java25-floor"),
        pytest.param("26.2", "java25", id="java25"),
    ],
)
def test_paper_runtime_deployment_spec_002_nominal_java_variant_matches_version(
    minecraft_version: str,
    java_tag: str,
) -> None:
    """Test 002 - Nominal
    Condition: Servers span Minecraft versions with differing Java requirements
    Result: The image reference uses the matching itzg Java variant tag
    """
    # Arrange
    runtime: PaperRuntime = PaperRuntime()
    server: Server = Server(
        name="version-probe",
        runtime=ServerRuntime.PAPER,
        minecraft_version=minecraft_version,
        cpu_millicores=PAPER_MINIMUM_CPU_MILLICORES,
        memory_bytes=PAPER_MINIMUM_MEMORY_BYTES,
    )

    # Act
    specification: DeploymentSpec = runtime.deployment_spec(server)

    # Assert
    assert specification.image_reference == f"{PAPER_IMAGE_REPOSITORY}:{java_tag}"


@pytest.mark.parametrize(
    ("requested", "resolved"),
    [
        pytest.param(None, "26.2", id="default-is-latest"),
        pytest.param("1.21.3", "1.21.3", id="listed-version"),
    ],
)
async def test_paper_runtime_resolve_version_003_nominal_published_version_is_resolved(
    requested: str | None,
    resolved: str,
) -> None:
    """Test 003 - Nominal
    Condition: The caller omits the version or requests one Paper publishes
    Result: The latest or requested Minecraft version is returned
    """
    # Arrange
    runtime: PaperRuntime
    requests: list[httpx.Request]
    runtime, requests = fill_runtime()

    # Act
    version: str = await runtime.resolve_version(requested)

    # Assert
    assert version == resolved
    assert [str(request.url) for request in requests] == [PAPER_FILL_PROJECT_URL]
    assert requests[0].headers["User-Agent"] == PAPER_FILL_USER_AGENT


async def test_paper_runtime_resolve_version_004_anomalous_unpublished_version_is_rejected() -> (
    None
):
    """Test 004 - Anomalous
    Condition: The caller requests a version Paper publishes no build for
    Result: ServerVersionUnsupportedError("paper does not support Minecraft version '1.2.5'")
    """
    # Arrange
    runtime: PaperRuntime
    runtime, _ = fill_runtime()

    # Act / Assert
    with pytest.raises(
        ServerVersionUnsupportedError,
        match=r"paper does not support Minecraft version '1\.2\.5'",
    ):
        await runtime.resolve_version("1.2.5")


async def test_paper_runtime_list_versions_005_nominal_families_are_flattened_in_order() -> None:
    """Test 005 - Nominal
    Condition: The Fill API returns version families keyed newest first
    Result: The families are flattened into one newest-first version list
    """
    # Arrange
    runtime: PaperRuntime
    runtime, _ = fill_runtime()

    # Act
    versions: list[str] = await runtime.list_versions()

    # Assert
    assert versions == FILL_VERSIONS_FLATTENED


@pytest.mark.parametrize(
    ("payload", "status_code", "message"),
    [
        pytest.param(
            FILL_VERSIONS_PAYLOAD,
            503,
            f"failed to fetch Paper versions from {PAPER_FILL_PROJECT_URL}",
            id="http-error",
        ),
        pytest.param(
            {"project": "paper"},
            200,
            f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}",
            id="missing-versions-key",
        ),
        pytest.param(
            {"versions": {"26.2": "26.2"}},
            200,
            f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}",
            id="family-not-a-list",
        ),
        pytest.param(
            {"versions": {}},
            200,
            f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}",
            id="no-versions",
        ),
        pytest.param(
            b"not-json",
            200,
            f"unexpected Paper version payload from {PAPER_FILL_PROJECT_URL}",
            id="invalid-json",
        ),
    ],
)
async def test_paper_runtime_list_versions_006_anomalous_version_source_failure_is_typed(
    payload: object,
    status_code: int,
    message: str,
) -> None:
    """Test 006 - Anomalous
    Condition: The Fill API fails or returns a payload without usable versions
    Result: RuntimeVersionSourceError describing the Fill URL is raised
    """
    # Arrange
    runtime: PaperRuntime
    runtime, _ = fill_runtime(payload=payload, status_code=status_code)

    # Act / Assert
    with pytest.raises(RuntimeVersionSourceError, match=message):
        await runtime.list_versions()


async def test_paper_runtime_list_versions_007_anomalous_transport_failure_is_typed() -> None:
    """Test 007 - Anomalous
    Condition: The Fill API request fails before any HTTP response arrives
    Result: RuntimeVersionSourceError describing the Fill URL is raised
    """

    # Arrange
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    runtime: PaperRuntime = PaperRuntime(transport=httpx.MockTransport(refuse))

    # Act / Assert
    with pytest.raises(
        RuntimeVersionSourceError,
        match=f"failed to fetch Paper versions from {PAPER_FILL_PROJECT_URL}",
    ):
        await runtime.list_versions()
