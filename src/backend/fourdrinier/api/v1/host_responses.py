"""
host_responses.py

Map host domain and persistence results to public API response schemas.
"""

from __future__ import annotations

from fourdrinier.db.models import DockerHostDetails, Host, KubernetesHostDetails
from fourdrinier.db.schemas import (
    DockerHostRead,
    DockerPingResponse,
    HostPingResponse,
    HostRead,
    KubernetesHostRead,
    KubernetesPingResponse,
    PingHostKey,
)
from fourdrinier.hosts import HostPingResult, HostProviderMismatchError, HostType
from fourdrinier.hosts.docker import DockerHostPingResult
from fourdrinier.hosts.kubernetes import KubernetesHostPingResult


def host_response(host: Host) -> HostRead:
    """Build the provider-specific public representation of a host.

    Args:
        host: Complete host aggregate to expose.

    Returns:
        A response without secret or bulky trust material.

    Raises:
        HostProviderMismatchError: If the aggregate lacks matching provider details.
    """
    if host.type is HostType.DOCKER:
        details: DockerHostDetails | None = host.docker_details
        if details is None:
            raise HostProviderMismatchError(
                f"Docker host {host.id} has no Docker details",
                provider=HostType.DOCKER,
            )
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

    kubernetes_details: KubernetesHostDetails | None = host.kubernetes_details
    if kubernetes_details is None:
        raise HostProviderMismatchError(
            f"Kubernetes host {host.id} has no Kubernetes details",
            provider=HostType.KUBERNETES,
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


def ping_response(result: HostPingResult) -> HostPingResponse:
    """Build the provider-specific public representation of a ping result.

    Args:
        result: Provider result returned through the host driver boundary.

    Returns:
        The matching provider ping response.

    Raises:
        HostProviderMismatchError: If the result type is not supported.
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
    if isinstance(result, KubernetesHostPingResult):
        return KubernetesPingResponse(
            latency_ms=result.latency_ms,
            git_version=result.git_version,
            platform=result.platform,
            username=result.username,
            namespace=result.namespace,
        )
    raise HostProviderMismatchError(
        f"unsupported ping result {type(result).__name__}",
        provider=result.type,
    )


__all__: list[str] = ["host_response", "ping_response"]
