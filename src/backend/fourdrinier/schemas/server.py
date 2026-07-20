"""
server.py

Define request and response contracts for logical Minecraft servers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from fourdrinier.servers.types import (
    DEFAULT_SERVER_CPU_MILLICORES,
    DEFAULT_SERVER_MEMORY_BYTES,
    ServerRuntime,
)


class ServerCreate(BaseModel):
    """Define a request to save a logical server configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    runtime: ServerRuntime
    minecraft_version: str | None = Field(default=None, min_length=1, max_length=32)
    cpu_millicores: int = Field(default=DEFAULT_SERVER_CPU_MILLICORES, gt=0)
    memory_bytes: int = Field(default=DEFAULT_SERVER_MEMORY_BYTES, gt=0)


class ServerUpdate(BaseModel):
    """Define editable metadata, version, and resource allocation for a saved logical server."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    minecraft_version: str | None = Field(default=None, min_length=1, max_length=32)
    cpu_millicores: int | None = Field(default=None, gt=0)
    memory_bytes: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> ServerUpdate:
        """Reject null for fields whose persisted values cannot be null.

        Returns:
            The validated partial update.

        Raises:
            ValueError: If the caller explicitly supplies null for an update field.
        """
        field_name: str
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ServerRead(BaseModel):
    """Represent a provider-independent saved server configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    runtime: ServerRuntime
    minecraft_version: str
    cpu_millicores: int
    memory_bytes: int
    desired_state: Literal["running", "stopped"]
    spec_generation: int
    created_at: datetime
    updated_at: datetime


type ServerListResponse = list[ServerRead]

__all__: list[str] = ["ServerCreate", "ServerListResponse", "ServerRead", "ServerUpdate"]
