"""
types.py

Define provider-independent logical server value types.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class ServerRuntime(StrEnum):
    """Minecraft runtimes supported by Fourdrinier."""

    PAPER = "paper"
    PUMPKIN = "pumpkin"


class ServerDesiredState(StrEnum):
    """Operational states a user can request for a logical server."""

    RUNNING = "running"
    STOPPED = "stopped"


type ServerId = UUID

DEFAULT_SERVER_CPU_MILLICORES: int = 1_000
DEFAULT_SERVER_MEMORY_BYTES: int = 2 * 1024 * 1024 * 1024


__all__: list[str] = [
    "DEFAULT_SERVER_CPU_MILLICORES",
    "DEFAULT_SERVER_MEMORY_BYTES",
    "ServerDesiredState",
    "ServerId",
    "ServerRuntime",
]
