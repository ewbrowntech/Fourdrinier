"""httpx client construction for talking to a Kubernetes API server."""

from __future__ import annotations

import ssl

import httpx

from fourdrinier.hosts.kubernetes.errors import TLSVerificationError

DEFAULT_TIMEOUT_SECONDS: float = 10.0


def build_ssl_context(ca_cert_pem: str) -> ssl.SSLContext:
    """Build a verifying SSL context that trusts only the cluster CA.

    ``cadata`` loads the PEM from memory — no temp files. Hostname checking
    stays on; the k3s serving certificate carries the API server's SANs.
    """
    try:
        return ssl.create_default_context(cadata=ca_cert_pem)
    except ssl.SSLError as exc:
        raise TLSVerificationError("stored CA certificate could not be loaded") from exc


def build_client(
    *,
    api_url: str,
    token: str,
    ca_cert_pem: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Return an ``AsyncClient`` authenticated against ``api_url``.

    ``transport`` is an injection point for tests (``httpx.MockTransport``).
    """
    return httpx.AsyncClient(
        base_url=api_url,
        verify=build_ssl_context(ca_cert_pem),
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx.Timeout(timeout),
        transport=transport,
    )


__all__ = ["DEFAULT_TIMEOUT_SECONDS", "build_client", "build_ssl_context"]
