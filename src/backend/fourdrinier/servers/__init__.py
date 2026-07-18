"""
__init__.py

Export logical server domain types and failures.
"""

from fourdrinier.servers.errors import (
    ServerError,
    ServerNameConflictError,
    ServerNotFoundError,
)
from fourdrinier.servers.types import (
    PUMPKIN_MINECRAFT_VERSION,
    ServerDesiredState,
    ServerId,
    ServerRuntime,
)

__all__: list[str] = [
    "PUMPKIN_MINECRAFT_VERSION",
    "ServerDesiredState",
    "ServerError",
    "ServerId",
    "ServerNameConflictError",
    "ServerNotFoundError",
    "ServerRuntime",
]
