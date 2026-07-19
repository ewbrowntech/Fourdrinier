"""
test_pumpkin.py

Unit tests for PumpkinRuntime deployment translation.
"""

from __future__ import annotations

from fourdrinier.db.models import Server
from fourdrinier.servers.deployment import (
    ContainerPort,
    DeploymentSpec,
    GeneratedFile,
    NetworkProtocol,
    PersistentMount,
    ResourceAllocation,
    TcpHealthCheck,
)
from fourdrinier.servers.pumpkin import (
    PUMPKIN_CONFIGURATION,
    PUMPKIN_DATA_MOUNT_NAME,
    PUMPKIN_DATA_PATH,
    PUMPKIN_IMAGE_REFERENCE,
    PUMPKIN_MINECRAFT_VERSION,
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
    PUMPKIN_PORT,
    PumpkinRuntime,
)
from fourdrinier.servers.runtimes import RuntimeAdapter
from fourdrinier.servers.types import ServerRuntime


def test_pumpkin_runtime_deployment_spec_001_nominal_logical_server_is_translated() -> None:
    """Test 001 - Nominal
    Condition: A logical Pumpkin server is translated by the current runtime adapter
    Result: The complete official-image deployment specification is provider-neutral
    """
    # Arrange
    runtime: PumpkinRuntime = PumpkinRuntime()
    server: Server = Server(
        name="pumpkin-patch",
        runtime=ServerRuntime.PUMPKIN,
        minecraft_version=PUMPKIN_MINECRAFT_VERSION,
        cpu_millicores=2_750,
        memory_bytes=3_221_225_472,
    )
    expected: DeploymentSpec = DeploymentSpec(
        image_reference=PUMPKIN_IMAGE_REFERENCE,
        command=("/bin/pumpkin",),
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

    # Act
    result: DeploymentSpec = runtime.deployment_spec(server)

    # Assert
    assert result == expected
    assert runtime.runtime is ServerRuntime.PUMPKIN
    assert runtime.minecraft_version == "26.2"
    assert runtime.minimum_resources == ResourceAllocation(
        cpu_millicores=PUMPKIN_MINIMUM_CPU_MILLICORES,
        memory_bytes=PUMPKIN_MINIMUM_MEMORY_BYTES,
    )
    assert isinstance(runtime, RuntimeAdapter)
