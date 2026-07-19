"""
test_types.py

Unit tests for provider-neutral host value types.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID

import pytest

from fourdrinier.hosts.types import HostPingResult, HostType

_HOST_ID: UUID = UUID("00000000-0000-0000-0000-000000000001")
_OBSERVED_AT: datetime = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("host_type", "expected_value"),
    [
        pytest.param(HostType.DOCKER, "docker", id="docker"),
        pytest.param(HostType.KUBERNETES, "kubernetes", id="kubernetes"),
    ],
)
def test_host_type_001_nominal_provider_has_stable_value(
    host_type: HostType,
    expected_value: str,
) -> None:
    """Test 001 - Nominal
    Condition: A supported host provider type is selected
    Result: Its value matches the stable persistence and API representation
    """
    # Arrange
    provider: HostType = host_type

    # Act
    value: str = provider.value

    # Assert
    assert value == expected_value


def test_host_ping_result_002_nominal_shared_observations_are_retained() -> None:
    """Test 002 - Nominal
    Condition: A successful ping supplies valid provider-neutral observations
    Result: HostPingResult retains every supplied observation
    """
    # Arrange
    latency_ms: float = 12.5

    # Act
    result: HostPingResult = HostPingResult(
        host_id=_HOST_ID,
        type=HostType.DOCKER,
        latency_ms=latency_ms,
        observed_at=_OBSERVED_AT,
    )

    # Assert
    assert result.host_id == _HOST_ID
    assert result.type is HostType.DOCKER
    assert result.latency_ms == latency_ms
    assert result.observed_at is _OBSERVED_AT


def test_host_ping_result_003_anomalous_observations_are_mutated() -> None:
    """Test 003 - Anomalous
    Condition: A caller attempts to mutate an existing ping result
    Result: FrozenInstanceError("cannot assign to field 'latency_ms'") is raised
    """
    # Arrange
    result: HostPingResult = HostPingResult(
        host_id=_HOST_ID,
        type=HostType.DOCKER,
        latency_ms=12.5,
        observed_at=_OBSERVED_AT,
    )
    captured: pytest.ExceptionInfo[FrozenInstanceError]

    # Act
    with pytest.raises(FrozenInstanceError) as captured:
        result.latency_ms = 1.0  # type: ignore[misc]

    # Assert
    assert str(captured.value) == "cannot assign to field 'latency_ms'"


@pytest.mark.parametrize(
    "latency_ms",
    [
        pytest.param(-0.1, id="negative"),
        pytest.param(float("inf"), id="infinite"),
        pytest.param(float("nan"), id="not-a-number"),
    ],
)
def test_host_ping_result_004_anomalous_latency_is_invalid(latency_ms: float) -> None:
    """Test 004 - Anomalous
    Condition: A ping result has a negative or non-finite latency
    Result: ValueError("latency_ms must be a finite, non-negative number") is raised
    """
    # Arrange
    captured: pytest.ExceptionInfo[ValueError]

    # Act
    with pytest.raises(ValueError) as captured:
        HostPingResult(
            host_id=_HOST_ID,
            type=HostType.DOCKER,
            latency_ms=latency_ms,
            observed_at=_OBSERVED_AT,
        )

    # Assert
    assert str(captured.value) == "latency_ms must be a finite, non-negative number"


def test_host_ping_result_005_anomalous_observation_has_no_timezone() -> None:
    """Test 005 - Anomalous
    Condition: A ping observation timestamp has no timezone information
    Result: ValueError("observed_at must include timezone information") is raised
    """
    # Arrange
    observed_at: datetime = datetime(2026, 7, 16, 12, 0)
    captured: pytest.ExceptionInfo[ValueError]

    # Act
    with pytest.raises(ValueError) as captured:
        HostPingResult(
            host_id=_HOST_ID,
            type=HostType.KUBERNETES,
            latency_ms=1.0,
            observed_at=observed_at,
        )

    # Assert
    assert str(captured.value) == "observed_at must include timezone information"
