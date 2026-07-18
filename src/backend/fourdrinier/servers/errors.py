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


__all__: list[str] = ["ServerError", "ServerNameConflictError", "ServerNotFoundError"]
