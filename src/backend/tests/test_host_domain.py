"""Tests for the provider-neutral host vocabulary."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fourdrinier.hosts import (
    HostAuthenticationError,
    HostError,
    HostPingResult,
    HostRemoteError,
    HostType,
)


def test_host_type_uses_stable_provider_values() -> None:
    assert list(HostType) == [HostType.DOCKER, HostType.KUBERNETES]
    assert str(HostType.DOCKER) == "docker"
    assert HostType("kubernetes") is HostType.KUBERNETES


def test_ping_result_contains_only_shared_observations() -> None:
    observed_at = datetime.now(UTC)
    result = HostPingResult(
        host_id=uuid4(),
        type=HostType.DOCKER,
        latency_ms=12.5,
        observed_at=observed_at,
    )

    assert result.type is HostType.DOCKER
    assert result.latency_ms == 12.5
    assert result.observed_at is observed_at
    with pytest.raises(FrozenInstanceError):
        result.latency_ms = 1.0  # type: ignore[misc]


@pytest.mark.parametrize("latency_ms", [-0.1, float("inf"), float("nan")])
def test_ping_result_rejects_invalid_latency(latency_ms: float) -> None:
    with pytest.raises(ValueError, match="latency_ms"):
        HostPingResult(
            host_id=uuid4(),
            type=HostType.DOCKER,
            latency_ms=latency_ms,
            observed_at=datetime.now(UTC),
        )


def test_ping_result_requires_timezone_aware_observation() -> None:
    with pytest.raises(ValueError, match="timezone"):
        HostPingResult(
            host_id=uuid4(),
            type=HostType.KUBERNETES,
            latency_ms=1.0,
            observed_at=datetime.now(),
        )


def test_remote_errors_share_a_stable_provider_neutral_base() -> None:
    error = HostAuthenticationError(
        "remote credentials were rejected", provider=HostType.KUBERNETES
    )

    assert isinstance(error, HostRemoteError)
    assert isinstance(error, HostError)
    assert error.provider is HostType.KUBERNETES
    assert str(error) == "remote credentials were rejected"
