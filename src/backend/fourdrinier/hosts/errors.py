"""Stable, provider-neutral errors for host use cases and drivers."""

from __future__ import annotations

from fourdrinier.hosts.types import HostType


class HostError(RuntimeError):
    """Base class for errors exposed by the host domain."""

    def __init__(self, message: str, *, provider: HostType | None = None) -> None:
        super().__init__(message)
        self.provider = provider


class HostNotFoundError(HostError):
    """The requested local host does not exist."""


class HostNameConflictError(HostError):
    """A host with the requested globally unique name already exists."""


class HostKeypairNotFoundError(HostError):
    """The SSH keypair selected for a Docker host does not exist."""


class HostDriverUnavailableError(HostError):
    """The selected host driver cannot currently perform the operation."""


class HostRemoteError(HostError):
    """Base class for stable failures reported by a remote host driver."""


class HostUnreachableError(HostRemoteError):
    """The remote host or its provider API could not be reached."""


class HostAuthenticationError(HostRemoteError):
    """The remote provider rejected the configured credentials."""


class HostTrustVerificationError(HostRemoteError):
    """Remote identity or transport trust verification failed."""


class HostPermissionDeniedError(HostRemoteError):
    """Credentials are valid but lack a required remote permission."""


class HostInvalidRemoteStateError(HostRemoteError):
    """The provider returned a missing, malformed, or incompatible state."""


__all__ = [
    "HostAuthenticationError",
    "HostDriverUnavailableError",
    "HostError",
    "HostInvalidRemoteStateError",
    "HostKeypairNotFoundError",
    "HostNameConflictError",
    "HostNotFoundError",
    "HostPermissionDeniedError",
    "HostRemoteError",
    "HostTrustVerificationError",
    "HostUnreachableError",
]
