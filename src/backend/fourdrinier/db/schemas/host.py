"""Pydantic schemas for Host create/read payloads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fourdrinier.db.models.host import HostKind
from fourdrinier.db.schemas.host_connection import (
    DockerConnection,
    JsonObject,
    KubernetesConnection,
)

HostConnection = DockerConnection | KubernetesConnection


class HostCreate(BaseModel):
    """Payload to register a new host."""

    name: str = Field(min_length=1, max_length=255)
    kind: HostKind
    connection: HostConnection
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_connection_for_kind(self) -> HostCreate:
        if self.kind is HostKind.DOCKER and not isinstance(self.connection, DockerConnection):
            raise ValueError("connection must match docker shape when kind is docker")
        if self.kind is HostKind.KUBERNETES and not isinstance(
            self.connection, KubernetesConnection
        ):
            raise ValueError("connection must match kubernetes shape when kind is kubernetes")
        return self

    def connection_payload(self) -> JsonObject:
        """JSON-serializable connection dict for persistence."""
        return self.connection.model_dump(mode="json", exclude_none=True)


class HostRead(BaseModel):
    """Host as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    kind: HostKind
    enabled: bool
    connection: JsonObject
    labels: dict[str, str]
    created_at: datetime
    updated_at: datetime


__all__ = ["HostConnection", "HostCreate", "HostRead"]
