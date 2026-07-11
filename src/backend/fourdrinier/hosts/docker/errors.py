"""Typed errors for Docker host connectivity."""

from __future__ import annotations


class DockerHostError(RuntimeError):
    """Base error for Docker host connection failures."""


class SSHAuthError(DockerHostError):
    """SSH authentication was rejected by the remote host."""


class HostUnreachableError(DockerHostError):
    """The remote host or its Docker daemon could not be reached."""


class HostKeyMismatchError(DockerHostError):
    """The remote host presented a key different from the recorded one."""


__all__ = [
    "DockerHostError",
    "HostKeyMismatchError",
    "HostUnreachableError",
    "SSHAuthError",
]
