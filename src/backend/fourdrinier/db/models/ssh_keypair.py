"""SSHKeypair ORM model — reusable SSH credentials for Docker hosts."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, LargeBinary, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from fourdrinier.db.base import Base


class KeypairSource(str, enum.Enum):
    """How the keypair entered the system."""

    GENERATED = "generated"
    UPLOADED = "uploaded"


def _keypair_source_values(enum_cls: type[KeypairSource]) -> list[str]:
    return [member.value for member in enum_cls]


class SSHKeypair(Base):
    """An SSH keypair; the private key is stored Fernet-encrypted."""

    __tablename__ = "ssh_keypairs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source: Mapped[KeypairSource] = mapped_column(
        Enum(
            KeypairSource,
            name="keypair_source",
            native_enum=False,
            values_callable=_keypair_source_values,
            length=32,
        ),
        nullable=False,
    )
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    private_key_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


__all__ = ["KeypairSource", "SSHKeypair"]
