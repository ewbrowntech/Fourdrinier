"""Kubernetes host operations: ping the API server, verify identity and RBAC."""

from __future__ import annotations

import ssl
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, NoReturn

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.crypto import decrypt_secret
from fourdrinier.core.settings import Settings
from fourdrinier.db.models import KubernetesHost
from fourdrinier.hosts.kubernetes.client import build_client
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)


@dataclass(frozen=True)
class PingResult:
    """Outcome of a successful cluster ping."""

    latency_ms: float
    git_version: str
    platform: str
    username: str
    namespace: str


def _raise_for_transport(exc: httpx.HTTPError, api_url: str) -> NoReturn:
    """Map a transport-level httpx error to a typed error.

    TLS failures arrive wrapped (usually ``ConnectError`` with an
    ``ssl.SSLCertVerificationError`` cause), so walk the exception chain.
    """
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


def _check_response(resp: httpx.Response, api_url: str) -> None:
    """Reject non-2xx responses with the matching typed error."""
    if resp.is_success:
        return
    if resp.status_code == 401:
        raise KubernetesAuthError(f"cluster {api_url!r} rejected the bearer token (401)")
    if resp.status_code == 403:
        # SelfSubjectReview/SelfSubjectAccessReview creation is granted to all
        # authenticated users via system:basic-user; a 403 means broken RBAC.
        raise KubernetesRBACError(
            f"cluster {api_url!r} denied the request (403): "
            "the service account's RBAC bindings are missing or broken"
        )
    raise ClusterUnreachableError(
        f"unexpected response {resp.status_code} from {resp.request.url.path} on {api_url!r}"
    )


def _parse_json(resp: httpx.Response, api_url: str) -> dict[str, Any]:
    try:
        body = resp.json()
    except ValueError as exc:
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned a non-JSON payload from {resp.request.url.path}"
        ) from exc
    if not isinstance(body, dict):
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned an unexpected payload from {resp.request.url.path}"
        )
    return body


async def _ping_cluster(
    *,
    api_url: str,
    token: str,
    ca_cert_pem: str,
    namespace: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> PingResult:
    """Ping a cluster: version, authenticated identity, and RBAC check.

    Boundary function — monkeypatched in API tests; ``transport`` allows
    unit testing with ``httpx.MockTransport``.
    """
    async with build_client(
        api_url=api_url, token=token, ca_cert_pem=ca_cert_pem, transport=transport
    ) as client:
        started: float = perf_counter()
        try:
            version_resp = await client.get("/version")
            _check_response(version_resp, api_url)

            ssr_resp = await client.post(
                "/apis/authentication.k8s.io/v1/selfsubjectreviews",
                json={
                    "apiVersion": "authentication.k8s.io/v1",
                    "kind": "SelfSubjectReview",
                },
            )
            _check_response(ssr_resp, api_url)

            ssar_resp = await client.post(
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
            _check_response(ssar_resp, api_url)
        except httpx.HTTPError as exc:
            _raise_for_transport(exc, api_url)
        latency_ms: float = (perf_counter() - started) * 1000

    version_info = _parse_json(version_resp, api_url)

    ssr_body = _parse_json(ssr_resp, api_url)
    try:
        username: str = ssr_body["status"]["userInfo"]["username"]
    except (KeyError, TypeError) as exc:
        raise ClusterUnreachableError(
            f"cluster {api_url!r} returned an unexpected SelfSubjectReview payload"
        ) from exc

    ssar_body = _parse_json(ssar_resp, api_url)
    ssar_status: dict[str, Any] = ssar_body.get("status") or {}
    if ssar_status.get("allowed") is not True:
        reason: str = str(ssar_status.get("reason", "")).strip()
        message: str = (
            f"service account {username!r} may not create deployments in namespace {namespace!r}"
        )
        if reason:
            message = f"{message}: {reason}"
        raise KubernetesRBACError(message)

    return PingResult(
        latency_ms=round(latency_ms, 1),
        git_version=str(version_info.get("gitVersion", "")),
        platform=str(version_info.get("platform", "")),
        username=username,
        namespace=namespace,
    )


async def ping_host(
    session: AsyncSession, host: KubernetesHost, settings: Settings | None = None
) -> PingResult:
    """Ping ``host`` over HTTPS and persist ``last_seen_at``.

    Raises:
        KubernetesAuthError: the cluster rejected the bearer token.
        KubernetesRBACError: the service account lacks required permissions.
        TLSVerificationError: server certificate not signed by the stored CA.
        ClusterUnreachableError: API server unreachable or misbehaving.
        DecryptionError / EncryptionKeyError: stored token cannot be decrypted.
    """
    token: str = decrypt_secret(host.token_encrypted, settings).decode()
    result: PingResult = await _ping_cluster(
        api_url=host.api_url,
        token=token,
        ca_cert_pem=host.ca_cert_pem,
        namespace=host.namespace,
    )

    host.last_seen_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(host)
    return result


__all__ = ["PingResult", "ping_host"]
