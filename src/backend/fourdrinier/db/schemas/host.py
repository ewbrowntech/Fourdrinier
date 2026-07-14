"""
host.py

Define request and response contracts for Docker and Kubernetes hosts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, ClassVar, Literal

from cryptography import x509
from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

_ADDRESS_PATTERN: str = r"^[A-Za-z0-9._\-]+$"
_USERNAME_PATTERN: str = r"^[A-Za-z0-9._\-]+$"
_NAMESPACE_PATTERN: str = r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$"


def _validate_https_url(value: str) -> str:
    url: AnyHttpUrl = AnyHttpUrl(value)
    if url.scheme != "https":
        raise ValueError("api_url must be an https:// URL")
    return str(url).rstrip("/")


type HttpsUrl = Annotated[
    str,
    Field(max_length=512),
    AfterValidator(_validate_https_url),
]


class HostCreateBase(BaseModel):
    """Define fields shared by every host creation request."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)


class DockerHostCreate(HostCreateBase):
    """Define a request to register a Docker host reachable over SSH."""

    type: Literal["docker"]
    address: str = Field(max_length=255, pattern=_ADDRESS_PATTERN)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(max_length=255, pattern=_USERNAME_PATTERN)
    keypair_id: uuid.UUID


class KubernetesHostCreate(HostCreateBase):
    """Define a request to register a Kubernetes cluster over HTTPS."""

    type: Literal["kubernetes"]
    api_url: HttpsUrl
    ca_cert_pem: str
    token: str = Field(min_length=1)
    namespace: str = Field(default="fourdrinier", max_length=63, pattern=_NAMESPACE_PATTERN)

    @field_validator("ca_cert_pem")
    @classmethod
    def validate_ca_certificate(cls, value: str) -> str:
        """Validate that trust material contains at least one PEM certificate.

        Args:
            value: PEM-encoded certificate bundle supplied by the caller.

        Returns:
            The unchanged PEM certificate bundle.

        Raises:
            ValueError: If the value is not a non-empty PEM certificate bundle.
        """
        try:
            _certificates: list[x509.Certificate] = x509.load_pem_x509_certificates(value.encode())
        except ValueError as exc:
            raise ValueError("ca_cert_pem is not a valid PEM certificate bundle") from exc
        return value


type HostCreate = Annotated[
    DockerHostCreate | KubernetesHostCreate,
    Field(discriminator="type"),
]


class HostReadBase(BaseModel):
    """Define fields shared by every host response."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    enabled: bool
    labels: dict[str, str]
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DockerHostRead(HostReadBase):
    """Represent a Docker host without private SSH key material."""

    type: Literal["docker"] = "docker"
    address: str
    port: int
    username: str
    keypair_id: uuid.UUID
    host_key_fingerprint: str | None


class KubernetesHostRead(HostReadBase):
    """Represent a Kubernetes host without credentials or trust material."""

    type: Literal["kubernetes"] = "kubernetes"
    api_url: str
    namespace: str


type HostRead = Annotated[
    DockerHostRead | KubernetesHostRead,
    Field(discriminator="type"),
]
type HostListResponse = list[HostRead]


class PingHostKey(BaseModel):
    """Represent Docker SSH host-key information observed by a ping."""

    fingerprint: str
    key_type: str
    first_seen: bool


class DockerPingResponse(BaseModel):
    """Represent a successful Docker host connectivity check."""

    status: Literal["ok"] = "ok"
    type: Literal["docker"] = "docker"
    latency_ms: float
    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: PingHostKey


class KubernetesPingResponse(BaseModel):
    """Represent a successful Kubernetes connectivity and RBAC check."""

    status: Literal["ok"] = "ok"
    type: Literal["kubernetes"] = "kubernetes"
    latency_ms: float
    git_version: str
    platform: str
    username: str
    namespace: str
    can_create_deployments: Literal[True] = True


type HostPingResponse = Annotated[
    DockerPingResponse | KubernetesPingResponse,
    Field(discriminator="type"),
]
type PingResponse = HostPingResponse

__all__: list[str] = [
    "DockerHostCreate",
    "DockerHostRead",
    "DockerPingResponse",
    "HostCreate",
    "HostCreateBase",
    "HostListResponse",
    "HostPingResponse",
    "HostRead",
    "HostReadBase",
    "HttpsUrl",
    "KubernetesHostCreate",
    "KubernetesHostRead",
    "KubernetesPingResponse",
    "PingHostKey",
    "PingResponse",
]
