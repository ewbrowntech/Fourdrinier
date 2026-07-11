"""Pydantic schemas for SSH keypair payloads. Private keys are never emitted."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fourdrinier.db.models.ssh_keypair import KeypairSource


class KeypairCreate(BaseModel):
    """Payload to create a keypair.

    Omit ``private_key`` to have the server generate an ed25519 keypair;
    provide it to import an existing (unencrypted) private key.
    """

    name: str = Field(min_length=1, max_length=255)
    private_key: str | None = Field(
        default=None,
        description="Unencrypted private key (OpenSSH or PEM). Omit to generate.",
    )


class KeypairRead(BaseModel):
    """Keypair as returned by the API — public material only."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    source: KeypairSource
    algorithm: str
    public_key: str
    fingerprint: str
    created_at: datetime
    updated_at: datetime


__all__ = ["KeypairCreate", "KeypairRead"]
