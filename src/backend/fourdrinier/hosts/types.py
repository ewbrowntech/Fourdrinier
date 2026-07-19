"""Provider-neutral value types used by the host domain."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import TypeAlias
from uuid import UUID


class HostType(StrEnum):
    """Host providers supported by Fourdrinier."""

    DOCKER = "docker"
    KUBERNETES = "kubernetes"


# Domain-facing aliases keep provider identities out of application and driver
# signatures without introducing runtime wrappers that ORM and API layers must
# unwrap.
HostId: TypeAlias = UUID
SSHKeypairId: TypeAlias = UUID
Timestamp: TypeAlias = datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class HostPingResult:
    """Provider-neutral outcome of a successful connectivity check.

    Provider drivers may extend this result with typed provider observations.
    Failures are represented by the exceptions in :mod:`fourdrinier.hosts.errors`,
    so a result never needs a second success flag.
    """

    host_id: HostId
    type: HostType
    latency_ms: float
    observed_at: Timestamp

    def __post_init__(self) -> None:
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError("latency_ms must be a finite, non-negative number")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must include timezone information")


__all__ = [
    "HostId",
    "HostPingResult",
    "HostType",
    "SSHKeypairId",
    "Timestamp",
]
