"""
types.py

Define Kubernetes-specific host operation result types.
"""

from __future__ import annotations

from dataclasses import dataclass

from fourdrinier.hosts.types import HostPingResult


@dataclass(frozen=True, slots=True, kw_only=True)
class KubernetesHostPingResult(HostPingResult):
    """Include Kubernetes observations with a provider-neutral ping result."""

    git_version: str
    platform: str
    username: str
    namespace: str


__all__: list[str] = ["KubernetesHostPingResult"]
