"""Pydantic schemas for host payloads (Docker and Kubernetes)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from cryptography import x509
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    field_validator,
)

# Excludes characters that would change the meaning of the ssh:// URL the
# backend builds from these fields.
_ADDRESS_PATTERN = r"^[A-Za-z0-9._\-]+$"
_USERNAME_PATTERN = r"^[A-Za-z0-9._\-]+$"

# RFC 1123 DNS label — the only shape Kubernetes accepts for namespace names.
_NAMESPACE_PATTERN = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"


def _validate_https_url(v: str) -> str:
    url = AnyHttpUrl(v)  # raises ValueError -> 422
    if url.scheme != "https":
        raise ValueError("api_url must be an https:// URL")
    return str(url).rstrip("/")


HttpsUrl = Annotated[str, Field(max_length=512), AfterValidator(_validate_https_url)]


class DockerHostCreate(BaseModel):
    """Payload to register a Docker host reachable over SSH."""

    type: Literal["docker"] = "docker"
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(max_length=255, pattern=_ADDRESS_PATTERN)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(max_length=255, pattern=_USERNAME_PATTERN)
    keypair_id: uuid.UUID
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)


class KubernetesHostCreate(BaseModel):
    """Payload to register a Kubernetes cluster reachable over HTTPS.

    ``token`` is a ServiceAccount bearer token; it is stored encrypted and is
    never returned by the API. ``ca_cert_pem`` is the cluster CA used to
    verify the API server's TLS certificate.
    """

    type: Literal["kubernetes"] = "kubernetes"
    name: str = Field(min_length=1, max_length=255)
    api_url: HttpsUrl
    ca_cert_pem: str
    token: str = Field(min_length=1)
    namespace: str = Field(
        default="fourdrinier", max_length=63, pattern=_NAMESPACE_PATTERN
    )
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("ca_cert_pem")
    @classmethod
    def _validate_ca(cls, v: str) -> str:
        try:
            certs = x509.load_pem_x509_certificates(v.encode())
        except ValueError as exc:
            raise ValueError(
                "ca_cert_pem is not a valid PEM certificate bundle"
            ) from exc
        if not certs:
            raise ValueError("ca_cert_pem contains no certificates")
        return v


def _host_create_tag(v: object) -> str | None:
    """Discriminate create payloads, defaulting missing ``type`` to docker.

    Plain ``Field(discriminator=...)`` rejects input without the tag key;
    existing clients registered Docker hosts before ``type`` existed.
    """
    if isinstance(v, dict):
        return v.get("type", "docker")
    return getattr(v, "type", None)


HostCreate = Annotated[
    Annotated[DockerHostCreate, Tag("docker")]
    | Annotated[KubernetesHostCreate, Tag("kubernetes")],
    Discriminator(_host_create_tag),
]


class DockerHostRead(BaseModel):
    """Docker host as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: Literal["docker"] = "docker"
    name: str
    address: str
    port: int
    username: str
    keypair_id: uuid.UUID
    enabled: bool
    labels: dict[str, str]
    host_key_fingerprint: str | None
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KubernetesHostRead(BaseModel):
    """Kubernetes host as returned by the API.

    Deliberately excludes the bearer token (secret) and CA PEM (bulky).
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: Literal["kubernetes"] = "kubernetes"
    name: str
    api_url: str
    namespace: str
    enabled: bool
    labels: dict[str, str]
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


HostRead = Annotated[
    DockerHostRead | KubernetesHostRead, Field(discriminator="type")
]


class PingHostKey(BaseModel):
    """Host key information reported by a ping."""

    fingerprint: str
    key_type: str
    first_seen: bool


class DockerPingResponse(BaseModel):
    """Successful connectivity check against a host's Docker daemon."""

    status: str = "ok"
    type: Literal["docker"] = "docker"
    latency_ms: float
    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: PingHostKey


class KubernetesPingResponse(BaseModel):
    """Successful connectivity + auth + RBAC check against a cluster.

    An RBAC failure is reported as HTTP 403, never a 200, so
    ``can_create_deployments`` is always true here.
    """

    status: str = "ok"
    type: Literal["kubernetes"] = "kubernetes"
    latency_ms: float
    git_version: str
    platform: str
    username: str
    namespace: str
    can_create_deployments: Literal[True] = True


PingResponse = Annotated[
    DockerPingResponse | KubernetesPingResponse, Field(discriminator="type")
]


__all__ = [
    "DockerHostCreate",
    "DockerHostRead",
    "DockerPingResponse",
    "HostCreate",
    "HostRead",
    "KubernetesHostCreate",
    "KubernetesHostRead",
    "KubernetesPingResponse",
    "PingHostKey",
    "PingResponse",
]
