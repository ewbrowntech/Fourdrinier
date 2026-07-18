"""
types.py

Define provider-independent server value types and current Pumpkin defaults.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class ServerRuntime(StrEnum):
    """Minecraft runtimes supported by Fourdrinier."""

    PUMPKIN = "pumpkin"


class ServerDesiredState(StrEnum):
    """Operational states a user can request for a logical server."""

    RUNNING = "running"
    STOPPED = "stopped"


type ServerId = UUID

# Phase 1 freezes the version reported by the current upstream Pumpkin runtime.
# The runtime catalog introduced in phase 2 will own version discovery.
PUMPKIN_MINECRAFT_VERSION: str = "26.2"


__all__: list[str] = [
    "PUMPKIN_MINECRAFT_VERSION",
    "ServerDesiredState",
    "ServerId",
    "ServerRuntime",
]
