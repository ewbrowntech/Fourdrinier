"""DockerHost ORM model — remote Docker daemons reached over SSH."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from fourdrinier.db.base import Base
from fourdrinier.db.models.ssh_keypair import SSHKeypair


class DockerHost(Base):
    """A remote Docker daemon reachable via ``ssh://username@address:port``.

    The ``host_key_*`` columns implement trust-on-first-use: they are NULL
    until the first successful connection records the server's host key, after
    which any mismatch is rejected.
    """

    __tablename__ = "docker_hosts"
    __table_args__ = (Index("ix_docker_hosts_enabled", "enabled"),)

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=22,
        server_default=text("22"),
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    keypair_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ssh_keypairs.id"),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=true(),
        default=True,
    )
    labels: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
    )
    host_key_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    host_key_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_key_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
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

    keypair: Mapped[SSHKeypair] = relationship(lazy="joined")


__all__ = ["DockerHost"]
