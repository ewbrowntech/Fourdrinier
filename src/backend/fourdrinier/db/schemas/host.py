"""Pydantic schemas for DockerHost payloads."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Excludes characters that would change the meaning of the ssh:// URL the
# backend builds from these fields.
_ADDRESS_PATTERN = r"^[A-Za-z0-9._\-]+$"
_USERNAME_PATTERN = r"^[A-Za-z0-9._\-]+$"


class DockerHostCreate(BaseModel):
    """Payload to register a Docker host reachable over SSH."""

    name: str = Field(min_length=1, max_length=255)
    address: str = Field(max_length=255, pattern=_ADDRESS_PATTERN)
    port: int = Field(default=22, ge=1, le=65535)
    username: str = Field(max_length=255, pattern=_USERNAME_PATTERN)
    keypair_id: uuid.UUID
    enabled: bool = True
    labels: dict[str, str] = Field(default_factory=dict)


class DockerHostRead(BaseModel):
    """Docker host as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
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


class PingHostKey(BaseModel):
    """Host key information reported by a ping."""

    fingerprint: str
    key_type: str
    first_seen: bool


class PingResponse(BaseModel):
    """Successful connectivity check against a host's Docker daemon."""

    status: str = "ok"
    latency_ms: float
    docker_version: str
    api_version: str
    os: str
    arch: str
    host_key: PingHostKey


__all__ = ["DockerHostCreate", "DockerHostRead", "PingHostKey", "PingResponse"]
