"""
ping.py

Check Kubernetes cluster connectivity, identity, and deployment permissions.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fourdrinier.core.secrets import EncryptedSecret, SecretDecryptor
from fourdrinier.db.models import Host, KubernetesHostDetails
from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostPermissionDeniedError,
    HostProviderMismatchError,
    HostTrustVerificationError,
    HostUnreachableError,
)
from fourdrinier.hosts.kubernetes import service as kubernetes_service
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.types import KubernetesHostPingResult
from fourdrinier.hosts.types import HostType


async def ping(host: Host, secret_decryptor: SecretDecryptor) -> KubernetesHostPingResult:
    """Check a Kubernetes host through its cluster API.

    Args:
        host: Host aggregate with Kubernetes details loaded.
        secret_decryptor: Decryptor for the stored Kubernetes bearer token.

    Returns:
        Shared and Kubernetes-specific observations from the cluster.

    Raises:
        HostProviderMismatchError: If the host is not a Kubernetes host.
        SecretError: If the stored bearer token cannot be decrypted.
        HostAuthenticationError: If the cluster rejects the bearer token.
        HostPermissionDeniedError: If the token lacks required permissions.
        HostTrustVerificationError: If TLS identity verification fails.
        HostUnreachableError: If the cluster cannot be reached or returns invalid data.
    """
    if host.type is not HostType.KUBERNETES:
        raise HostProviderMismatchError(
            f"the Kubernetes driver cannot operate on a {host.type.value} host",
            provider=HostType.KUBERNETES,
        )
    details: KubernetesHostDetails | None = host.kubernetes_details
    if details is None:
        raise HostProviderMismatchError(
            "the Kubernetes host has no Kubernetes details",
            provider=HostType.KUBERNETES,
        )

    token_bytes: bytes = secret_decryptor.decrypt(EncryptedSecret(details.token_encrypted))
    try:
        token: str = token_bytes.decode()
    except UnicodeDecodeError as exc:
        raise HostAuthenticationError(
            "the stored Kubernetes bearer token is not valid UTF-8",
            provider=HostType.KUBERNETES,
        ) from exc

    try:
        result: kubernetes_service.PingResult = await kubernetes_service._ping_cluster(
            api_url=details.api_url,
            token=token,
            ca_cert_pem=details.ca_cert_pem,
            namespace=details.namespace,
        )
    except KubernetesAuthError as exc:
        raise HostAuthenticationError(str(exc), provider=HostType.KUBERNETES) from exc
    except KubernetesRBACError as exc:
        raise HostPermissionDeniedError(str(exc), provider=HostType.KUBERNETES) from exc
    except TLSVerificationError as exc:
        raise HostTrustVerificationError(str(exc), provider=HostType.KUBERNETES) from exc
    except ClusterUnreachableError as exc:
        raise HostUnreachableError(str(exc), provider=HostType.KUBERNETES) from exc

    return KubernetesHostPingResult(
        host_id=host.id,
        type=HostType.KUBERNETES,
        latency_ms=result.latency_ms,
        observed_at=datetime.now(UTC),
        git_version=result.git_version,
        platform=result.platform,
        username=result.username,
        namespace=result.namespace,
    )


__all__: list[str] = ["ping"]
