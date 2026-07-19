"""Typed errors raised by Kubernetes host operations."""

from __future__ import annotations


class KubernetesHostError(RuntimeError):
    """Base class for Kubernetes host errors."""


class KubernetesAuthError(KubernetesHostError):
    """The cluster rejected the bearer token (HTTP 401)."""


class ClusterUnreachableError(KubernetesHostError):
    """The API server could not be reached or gave an unexpected response."""


class TLSVerificationError(KubernetesHostError):
    """The server certificate is not signed by the stored CA, or the CA is invalid."""


class KubernetesRBACError(KubernetesHostError):
    """The ServiceAccount lacks the permissions fourdrinier requires."""


__all__ = [
    "ClusterUnreachableError",
    "KubernetesAuthError",
    "KubernetesHostError",
    "KubernetesRBACError",
    "TLSVerificationError",
]
