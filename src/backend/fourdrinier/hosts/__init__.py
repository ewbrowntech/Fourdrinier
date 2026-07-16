"""
__init__.py

Expose the provider-neutral host domain vocabulary.
"""

from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostDriverUnavailableError,
    HostError,
    HostInvalidRemoteStateError,
    HostKeypairNotFoundError,
    HostNameConflictError,
    HostNotFoundError,
    HostPermissionDeniedError,
    HostRemoteError,
    HostTrustVerificationError,
    HostUnreachableError,
)
from fourdrinier.hosts.types import (
    HostId,
    HostPingResult,
    HostType,
    SSHKeypairId,
    Timestamp,
)

__all__ = [
    "HostAuthenticationError",
    "HostDriverUnavailableError",
    "HostError",
    "HostId",
    "HostInvalidRemoteStateError",
    "HostKeypairNotFoundError",
    "HostNameConflictError",
    "HostNotFoundError",
    "HostPermissionDeniedError",
    "HostPingResult",
    "HostRemoteError",
    "HostTrustVerificationError",
    "HostType",
    "HostUnreachableError",
    "SSHKeypairId",
    "Timestamp",
]
