"""Unit tests for the kubernetes ``_ping_cluster`` boundary via MockTransport."""

from __future__ import annotations

import json
import ssl
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.service import _ping_cluster
from tests.test_api_hosts_kubernetes import CA_PEM

API_URL = "https://203.0.113.20:6443"
USERNAME = "system:serviceaccount:fourdrinier:fourdrinier"

VERSION_BODY = {"gitVersion": "v1.31.4+k3s1", "platform": "linux/amd64"}
SSR_BODY = {"status": {"userInfo": {"username": USERNAME}}}
SSAR_ALLOWED = {"status": {"allowed": True}}


def _happy_handler(
    requests: list[httpx.Request] | None = None,
    ssar_body: dict[str, Any] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if request.url.path == "/version":
            return httpx.Response(200, json=VERSION_BODY)
        if request.url.path == "/apis/authentication.k8s.io/v1/selfsubjectreviews":
            return httpx.Response(201, json=SSR_BODY)
        if request.url.path == "/apis/authorization.k8s.io/v1/selfsubjectaccessreviews":
            return httpx.Response(201, json=ssar_body or SSAR_ALLOWED)
        return httpx.Response(404)

    return handler


async def _ping(handler: Callable[[httpx.Request], httpx.Response], namespace: str = "fourdrinier"):
    return await _ping_cluster(
        api_url=API_URL,
        token="token",
        ca_cert_pem=CA_PEM,
        namespace=namespace,
        transport=httpx.MockTransport(handler),
    )


async def test_ping_happy_path() -> None:
    requests: list[httpx.Request] = []
    result = await _ping(_happy_handler(requests), namespace="games")

    assert result.git_version == "v1.31.4+k3s1"
    assert result.platform == "linux/amd64"
    assert result.username == USERNAME
    assert result.namespace == "games"
    assert result.latency_ms >= 0

    # bearer token attached to every call
    assert all(r.headers["Authorization"] == "Bearer token" for r in requests)

    # the SSAR asks exactly for create-deployments in the host's namespace
    ssar = json.loads(requests[2].content)
    assert ssar["spec"]["resourceAttributes"] == {
        "namespace": "games",
        "verb": "create",
        "group": "apps",
        "resource": "deployments",
    }


async def test_401_raises_auth_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"kind": "Status"})

    with pytest.raises(KubernetesAuthError):
        await _ping(handler)


async def test_403_raises_rbac_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/version":
            return httpx.Response(200, json=VERSION_BODY)
        return httpx.Response(403, json={"kind": "Status"})

    with pytest.raises(KubernetesRBACError):
        await _ping(handler)


async def test_ssar_denied_raises_rbac_error() -> None:
    denied = {"status": {"allowed": False, "reason": "no RoleBinding"}}
    with pytest.raises(KubernetesRBACError, match="no RoleBinding"):
        await _ping(_happy_handler(ssar_body=denied))


async def test_connect_error_raises_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ClusterUnreachableError):
        await _ping(handler)


async def test_tls_failure_raises_tls_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        exc = httpx.ConnectError("TLS failure", request=request)
        exc.__cause__ = ssl.SSLCertVerificationError(
            "certificate verify failed: unable to get local issuer certificate"
        )
        raise exc

    with pytest.raises(TLSVerificationError):
        await _ping(handler)


async def test_unexpected_status_raises_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    with pytest.raises(ClusterUnreachableError):
        await _ping(handler)


async def test_malformed_ssr_raises_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/version":
            return httpx.Response(200, json=VERSION_BODY)
        if request.url.path == "/apis/authentication.k8s.io/v1/selfsubjectreviews":
            return httpx.Response(201, json={"status": {}})
        return httpx.Response(201, json=SSAR_ALLOWED)

    with pytest.raises(ClusterUnreachableError):
        await _ping(handler)
