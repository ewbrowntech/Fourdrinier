"""
server.py

Define request and response contracts for logical Minecraft servers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ServerCreate(BaseModel):
    """Define a request to save a Pumpkin server configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    runtime: Literal["pumpkin"] = "pumpkin"


class ServerUpdate(BaseModel):
    """Define editable metadata for a saved logical server."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> ServerUpdate:
        """Reject null for fields whose persisted values cannot be null.

        Returns:
            The validated partial update.

        Raises:
            ValueError: If the caller explicitly supplies null for an update field.
        """
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("name cannot be null")
        return self


class ServerRead(BaseModel):
    """Represent a provider-independent saved server configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    runtime: Literal["pumpkin"]
    minecraft_version: str
    desired_state: Literal["running", "stopped"]
    spec_generation: int
    created_at: datetime
    updated_at: datetime


type ServerListResponse = list[ServerRead]

__all__: list[str] = ["ServerCreate", "ServerListResponse", "ServerRead", "ServerUpdate"]
