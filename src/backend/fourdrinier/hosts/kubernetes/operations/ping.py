"""
ping.py

Check Kubernetes cluster connectivity, identity, and deployment permissions.
"""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, NoReturn

import httpx

from fourdrinier.core.secrets import EncryptedSecret, SecretDecryptor
from fourdrinier.db.models import Host, KubernetesHostDetails
from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostPermissionDeniedError,
    HostProviderMismatchError,
    HostTrustVerificationError,
    HostUnreachableError,
)
from fourdrinier.hosts.kubernetes.client import build_client
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.types import KubernetesHostPingResult
from fourdrinier.hosts.types import HostType


@dataclass(frozen=True, slots=True)
class KubernetesPingObservation:
    """Represent raw observations from a successful Kubernetes connectivity check."""

    latency_ms: float
    git_version: str
    platform: str
    username: str
    namespace: str


def _raise_for_transport(exc: httpx.HTTPError, api_url: str) -> NoReturn:
    cause: BaseException | None = exc
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if isinstance(cause, ssl.SSLCertVerificationError):
            raise TLSVerificationError(
                f"TLS verification failed for {api_url!r}: server certificate "
                "is not signed by the stored CA"
            ) from exc
        if isinstance(cause, ssl.SSLError):
            raise TLSVerificationError(f"TLS handshake with {api_url!r} failed: {cause}") from exc
        cause = cause.__cause__ or cause.__context__
    raise ClusterUnreachableError(f"could not reach {api_url!r}: {exc}") from exc


def _check_response(response: httpx.Response, api_url: str) -> None:
    if response.is_success:
        return
    if response.status_code == 401:
        raise KubernetesAuthError(f"cluster {api_url!r} rejected the bearer token (401)")
    if response.status_code == 403:
        raise KubernetesRBACError(
            f"cluster {api_url!r} denied the request (403): "
            "the service account's RBAC bindings are missing or broken"
        )
    raise ClusterUnreachableError(
        f"unexpected response {response.status_code} from "
        f"{response.request.url.path} on {api_url!r}"
    )


def _parse_json(response: httpx.Response, api_url: str) -> dict[str, Any]:
    try:
        body: Any = response.json()
    except ValueError as exc:
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned a non-JSON payload from {response.request.url.path}"
        ) from exc
    if not isinstance(body, dict):
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned an unexpected payload from {response.request.url.path}"
        )
    return body


async def _ping_remote(
    *,
    api_url: str,
    token: str,
    ca_cert_pem: str,
    namespace: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> KubernetesPingObservation:
    client: httpx.AsyncClient = build_client(
        api_url=api_url,
        token=token,
        ca_cert_pem=ca_cert_pem,
        transport=transport,
    )
    async with client:
        started: float = perf_counter()
        try:
            version_response: httpx.Response = await client.get("/version")
            _check_response(version_response, api_url)

            identity_response: httpx.Response = await client.post(
                "/apis/authentication.k8s.io/v1/selfsubjectreviews",
                json={
                    "apiVersion": "authentication.k8s.io/v1",
                    "kind": "SelfSubjectReview",
                },
            )
            _check_response(identity_response, api_url)

            access_response: httpx.Response = await client.post(
                "/apis/authorization.k8s.io/v1/selfsubjectaccessreviews",
                json={
                    "apiVersion": "authorization.k8s.io/v1",
                    "kind": "SelfSubjectAccessReview",
                    "spec": {
                        "resourceAttributes": {
                            "namespace": namespace,
                            "verb": "create",
                            "group": "apps",
                            "resource": "deployments",
                        }
                    },
                },
            )
            _check_response(access_response, api_url)
        except httpx.HTTPError as exc:
            _raise_for_transport(exc, api_url)
        latency_ms: float = (perf_counter() - started) * 1000

    version_info: dict[str, Any] = _parse_json(version_response, api_url)
    identity_body: dict[str, Any] = _parse_json(identity_response, api_url)
    try:
        username: str = identity_body["status"]["userInfo"]["username"]
    except (KeyError, TypeError) as exc:
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned an unexpected SelfSubjectReview payload"
        ) from exc

    access_body: dict[str, Any] = _parse_json(access_response, api_url)
    access_status: dict[str, Any] = access_body.get("status") or {}
    if access_status.get("allowed") is not True:
        reason: str = str(access_status.get("reason", "")).strip()
        message: str = (
            f"service account {username!r} may not create deployments in namespace {namespace!r}"
        )
        if reason:
            message = f"{message}: {reason}"
        raise KubernetesRBACError(message)

    return KubernetesPingObservation(
        latency_ms=round(latency_ms, 1),
        git_version=str(version_info.get("gitVersion", "")),
        platform=str(version_info.get("platform", "")),
        username=username,
        namespace=namespace,
    )


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
        result: KubernetesPingObservation = await _ping_remote(
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
