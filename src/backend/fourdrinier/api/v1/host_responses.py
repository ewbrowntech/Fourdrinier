"""
host_responses.py

Map host domain and persistence results to public API response schemas.
"""

from __future__ import annotations

from typing import cast

from fourdrinier.db.models import DockerHostDetails, Host, KubernetesHostDetails
from fourdrinier.hosts.docker import DockerHostPingResult
from fourdrinier.hosts.drivers import HostDriverPingResult
from fourdrinier.hosts.types import HostType
from fourdrinier.schemas import (
    DockerHostRead,
    DockerPingResponse,
    HostPingResponse,
    HostRead,
    KubernetesHostRead,
    KubernetesPingResponse,
    PingHostKey,
)


def host_response(host: Host) -> HostRead:
    """Build the provider-specific public representation of a host.

    Args:
        host: Complete host aggregate to expose.

    Returns:
        A response without secret or bulky trust material.
    """
    if host.type is HostType.DOCKER:
        details: DockerHostDetails = cast(DockerHostDetails, host.docker_details)
        return DockerHostRead(
            id=host.id,
            name=host.name,
            enabled=host.enabled,
            labels=host.labels,
            last_seen_at=host.last_seen_at,
            created_at=host.created_at,
            updated_at=host.updated_at,
            address=details.address,
            port=details.port,
            username=details.username,
            keypair_id=details.keypair_id,
            host_key_fingerprint=details.host_key_fingerprint,
        )

    kubernetes_details: KubernetesHostDetails = cast(
        KubernetesHostDetails,
        host.kubernetes_details,
    )
    return KubernetesHostRead(
        id=host.id,
        name=host.name,
        enabled=host.enabled,
        labels=host.labels,
        last_seen_at=host.last_seen_at,
        created_at=host.created_at,
        updated_at=host.updated_at,
        api_url=kubernetes_details.api_url,
        namespace=kubernetes_details.namespace,
    )


def ping_response(result: HostDriverPingResult) -> HostPingResponse:
    """Build the provider-specific public representation of a ping result.

    Args:
        result: Provider result returned through the host driver boundary.

    Returns:
        The matching provider ping response.
    """
    if isinstance(result, DockerHostPingResult):
        return DockerPingResponse(
            latency_ms=result.latency_ms,
            docker_version=result.docker_version,
            api_version=result.api_version,
            os=result.os,
            arch=result.arch,
            host_key=PingHostKey(
                fingerprint=result.host_key.fingerprint,
                key_type=result.host_key.key_type,
                first_seen=result.host_key.first_seen,
            ),
        )
    return KubernetesPingResponse(
        latency_ms=result.latency_ms,
        git_version=result.git_version,
        platform=result.platform,
        username=result.username,
        namespace=result.namespace,
    )


__all__: list[str] = ["host_response", "ping_response"]
