"""
test_server.py

Unit tests for logical server request contracts.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fourdrinier.schemas.server import ServerCreate, ServerUpdate
from fourdrinier.servers import (
    DEFAULT_SERVER_CPU_MILLICORES,
    DEFAULT_SERVER_MEMORY_BYTES,
    ServerRuntime,
)


def test_server_create_001_nominal_omitted_fields_receive_product_defaults() -> None:
    """Test 001 - Nominal
    Condition: Creation supplies a runtime but omits version and resource allocations
    Result: No version is pinned and product default allocations are assigned
    """
    # Arrange
    payload: dict[str, object] = {"name": "pumpkin-patch", "runtime": "pumpkin"}

    # Act
    request: ServerCreate = ServerCreate.model_validate(payload)

    # Assert
    assert request.runtime is ServerRuntime.PUMPKIN
    assert request.minecraft_version is None
    assert request.cpu_millicores == DEFAULT_SERVER_CPU_MILLICORES == 1_000
    assert request.memory_bytes == DEFAULT_SERVER_MEMORY_BYTES == 2_147_483_648


def test_server_create_004_anomalous_missing_runtime_is_rejected() -> None:
    """Test 004 - Anomalous
    Condition: Creation omits the runtime field
    Result: ValidationError is raised for the missing runtime
    """
    # Arrange
    payload: dict[str, object] = {"name": "runtimeless-world"}
    captured: pytest.ExceptionInfo[ValidationError]

    # Act
    with pytest.raises(ValidationError) as captured:
        ServerCreate.model_validate(payload)

    # Assert
    assert captured.value.error_count() == 1
    assert captured.value.errors()[0]["loc"] == ("runtime",)


def test_server_update_002_nominal_supplied_fields_are_accepted() -> None:
    """Test 002 - Nominal
    Condition: A partial update contains positive allocations and a Minecraft version
    Result: Every supplied field remains present in the validated update
    """
    # Arrange
    payload: dict[str, object] = {
        "minecraft_version": "26.2",
        "cpu_millicores": 1_500,
        "memory_bytes": 3_221_225_472,
    }

    # Act
    request: ServerUpdate = ServerUpdate.model_validate(payload)

    # Assert
    assert request.minecraft_version == "26.2"
    assert request.cpu_millicores == 1_500
    assert request.memory_bytes == 3_221_225_472
    assert request.model_fields_set == {"minecraft_version", "cpu_millicores", "memory_bytes"}


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"cpu_millicores": 0}, id="zero-cpu"),
        pytest.param({"memory_bytes": -1}, id="negative-memory"),
        pytest.param({"cpu_millicores": None}, id="null-cpu"),
        pytest.param({"memory_bytes": None}, id="null-memory"),
        pytest.param({"minecraft_version": None}, id="null-version"),
        pytest.param({"minecraft_version": ""}, id="empty-version"),
    ],
)
def test_server_update_003_anomalous_invalid_resources_are_rejected(
    payload: dict[str, object],
) -> None:
    """Test 003 - Anomalous
    Condition: A partial update contains a non-positive, explicit-null, or empty field value
    Result: ValidationError is raised for the invalid field
    """
    # Arrange
    captured: pytest.ExceptionInfo[ValidationError]

    # Act
    with pytest.raises(ValidationError) as captured:
        ServerUpdate.model_validate(payload)

    # Assert
    assert captured.value.error_count() == 1
