"""
__init__.py

Export logical server domain types and failures.
"""

from fourdrinier.servers.errors import (
    ServerError,
    ServerNameConflictError,
    ServerNotFoundError,
    ServerResourceMinimumError,
)
from fourdrinier.servers.pumpkin import (
    PUMPKIN_MINECRAFT_VERSION,
    PUMPKIN_MINIMUM_CPU_MILLICORES,
    PUMPKIN_MINIMUM_MEMORY_BYTES,
)
from fourdrinier.servers.types import (
    DEFAULT_SERVER_CPU_MILLICORES,
    DEFAULT_SERVER_MEMORY_BYTES,
    ServerDesiredState,
    ServerId,
    ServerRuntime,
)

__all__: list[str] = [
    "DEFAULT_SERVER_CPU_MILLICORES",
    "DEFAULT_SERVER_MEMORY_BYTES",
    "PUMPKIN_MINECRAFT_VERSION",
    "PUMPKIN_MINIMUM_CPU_MILLICORES",
    "PUMPKIN_MINIMUM_MEMORY_BYTES",
    "ServerDesiredState",
    "ServerError",
    "ServerId",
    "ServerNameConflictError",
    "ServerNotFoundError",
    "ServerResourceMinimumError",
    "ServerRuntime",
]
