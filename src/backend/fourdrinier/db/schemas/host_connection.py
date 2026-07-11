"""Pydantic schemas for host connection JSON validation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fourdrinier.db.models.host import HostKind

JsonObject = dict[str, Any]


class DockerConnection(BaseModel):
    """Reachability config for a Docker daemon/API endpoint."""

    model_config = ConfigDict(extra="forbid")

    host: str = Field(min_length=1, description="Docker host URL, e.g. unix:///var/run/docker.sock")
    tls: bool = False
    ca_ref: str | None = None
    cert_ref: str | None = None
    key_ref: str | None = None


class KubernetesConnection(BaseModel):
    """Reachability config for a Kubernetes cluster."""

    model_config = ConfigDict(extra="forbid")

    api_server: str = Field(min_length=1, description="Kubernetes API server URL")
    kubeconfig_ref: str | None = None
    context: str | None = None
    namespace_default: str | None = None


def validate_host_connection(kind: HostKind | str, connection: JsonObject) -> JsonObject:
    """Validate and normalize ``connection`` for the given host ``kind``.

    Returns a JSON-serializable dict suitable for persistence.
    Raises ``ValueError`` with a readable message on invalid input.
    """
    kind_value: HostKind = HostKind(kind) if not isinstance(kind, HostKind) else kind
    try:
        if kind_value is HostKind.DOCKER:
            parsed_docker: DockerConnection = DockerConnection.model_validate(connection)
            return parsed_docker.model_dump(mode="json", exclude_none=True)
        if kind_value is HostKind.KUBERNETES:
            parsed_k8s: KubernetesConnection = KubernetesConnection.model_validate(connection)
            return parsed_k8s.model_dump(mode="json", exclude_none=True)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
    raise ValueError(f"unsupported host kind: {kind_value!r}")


__all__ = [
    "DockerConnection",
    "JsonObject",
    "KubernetesConnection",
    "validate_host_connection",
]
