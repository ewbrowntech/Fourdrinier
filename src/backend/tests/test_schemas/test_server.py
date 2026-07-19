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
)


def test_server_create_001_nominal_omitted_resources_receive_product_defaults() -> None:
    """Test 001 - Nominal
    Condition: Creation omits CPU and memory allocation fields
    Result: The editable product defaults are assigned to the request
    """
    # Arrange
    payload: dict[str, object] = {"name": "pumpkin-patch"}

    # Act
    request: ServerCreate = ServerCreate.model_validate(payload)

    # Assert
    assert request.cpu_millicores == DEFAULT_SERVER_CPU_MILLICORES == 1_000
    assert request.memory_bytes == DEFAULT_SERVER_MEMORY_BYTES == 2_147_483_648


def test_server_update_002_nominal_positive_resources_are_accepted() -> None:
    """Test 002 - Nominal
    Condition: A partial update contains positive CPU and memory allocations
    Result: Both allocations remain present in the validated update
    """
    # Arrange
    payload: dict[str, object] = {
        "cpu_millicores": 1_500,
        "memory_bytes": 3_221_225_472,
    }

    # Act
    request: ServerUpdate = ServerUpdate.model_validate(payload)

    # Assert
    assert request.cpu_millicores == 1_500
    assert request.memory_bytes == 3_221_225_472
    assert request.model_fields_set == {"cpu_millicores", "memory_bytes"}


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"cpu_millicores": 0}, id="zero-cpu"),
        pytest.param({"memory_bytes": -1}, id="negative-memory"),
        pytest.param({"cpu_millicores": None}, id="null-cpu"),
        pytest.param({"memory_bytes": None}, id="null-memory"),
    ],
)
def test_server_update_003_anomalous_invalid_resources_are_rejected(
    payload: dict[str, object],
) -> None:
    """Test 003 - Anomalous
    Condition: A partial update contains a non-positive or explicit-null resource
    Result: ValidationError is raised for the invalid allocation
    """
    # Arrange
    captured: pytest.ExceptionInfo[ValidationError]

    # Act
    with pytest.raises(ValidationError) as captured:
        ServerUpdate.model_validate(payload)

    # Assert
    assert captured.value.error_count() == 1
