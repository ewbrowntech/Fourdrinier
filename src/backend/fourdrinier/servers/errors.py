"""
errors.py

Define stable failures for logical server use cases.
"""

from __future__ import annotations


class ServerError(RuntimeError):
    """Base class for errors exposed by the server domain."""


class ServerNotFoundError(ServerError):
    """The requested logical server does not exist."""


class ServerNameConflictError(ServerError):
    """A logical server already uses the requested name."""


class ServerResourceMinimumError(ServerError):
    """A resource allocation is below the selected runtime's minimum."""


class ServerVersionUnsupportedError(ServerError):
    """The selected runtime does not support the requested Minecraft version."""


class RuntimeNotRegisteredError(ServerError):
    """No runtime adapter is registered for the requested server runtime."""


class RuntimeVersionSourceError(ServerError):
    """The runtime's upstream version source could not be consulted."""


__all__: list[str] = [
    "RuntimeNotRegisteredError",
    "RuntimeVersionSourceError",
    "ServerError",
    "ServerNameConflictError",
    "ServerNotFoundError",
    "ServerResourceMinimumError",
    "ServerVersionUnsupportedError",
]
