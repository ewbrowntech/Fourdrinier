"""
__init__.py

Expose the provider-neutral host domain and driver boundary.
"""

from fourdrinier.hosts.drivers import HostDriver, HostDriverRegistry
from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostDriverNotRegisteredError,
    HostDriverUnavailableError,
    HostError,
    HostInvalidRemoteStateError,
    HostKeypairNotFoundError,
    HostNameConflictError,
    HostNotFoundError,
    HostPermissionDeniedError,
    HostProviderMismatchError,
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
    "HostDriver",
    "HostDriverNotRegisteredError",
    "HostDriverRegistry",
    "HostDriverUnavailableError",
    "HostError",
    "HostId",
    "HostInvalidRemoteStateError",
    "HostKeypairNotFoundError",
    "HostNameConflictError",
    "HostNotFoundError",
    "HostPermissionDeniedError",
    "HostPingResult",
    "HostProviderMismatchError",
    "HostRemoteError",
    "HostTrustVerificationError",
    "HostType",
    "HostUnreachableError",
    "SSHKeypairId",
    "Timestamp",
]
