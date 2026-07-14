"""Host aggregate ORM models and the legacy Docker host model.

The ``Host`` aggregate is the persistence target described by the host
architecture.  ``DockerHost`` remains temporarily available for the legacy
CRUD path and will be removed once that path has been replaced.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from fourdrinier.db.base import Base
from fourdrinier.db.models.ssh_keypair import SSHKeypair
from fourdrinier.hosts.types import HostType


def _host_type_values(enum_cls: type[HostType]) -> list[str]:
    """Persist the stable string values rather than enum member names."""

    return [member.value for member in enum_cls]


def _host_type_enum(*, create_constraint: bool) -> Enum:
    return Enum(
        HostType,
        name="host_type",
        native_enum=False,
        values_callable=_host_type_values,
        create_constraint=create_constraint,
        validate_strings=True,
        length=10,
    )


class Host(Base):
    """Provider-neutral identity and lifecycle state for a registered host."""

    __tablename__ = "hosts"
    __table_args__ = (
        UniqueConstraint("name", name="uq_hosts_name"),
        # Required as the target of the provider-aware composite foreign keys
        # on details tables.  It also makes the provider match enforceable by
        # the database rather than only by Python relationship code.
        UniqueConstraint("id", "type", name="uq_hosts_id_type"),
        Index("ix_hosts_enabled", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[HostType] = mapped_column(
        _host_type_enum(create_constraint=True),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    docker_details: Mapped[DockerHostDetails | None] = relationship(
        back_populates="host",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
        uselist=False,
    )
    kubernetes_details: Mapped[KubernetesHostDetails | None] = relationship(
        back_populates="host",
        cascade="all, delete-orphan",
        single_parent=True,
        passive_deletes=True,
        uselist=False,
    )


class DockerHostDetails(Base):
    """Connection and trust state specific to a Docker host."""

    __tablename__ = "docker_host_details"
    __table_args__ = (
        CheckConstraint("host_type = 'docker'", name="ck_docker_host_details_type"),
        ForeignKeyConstraint(
            ("host_id", "host_type"),
            ("hosts.id", "hosts.type"),
            name="fk_docker_host_details_host",
            ondelete="CASCADE",
        ),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    # The fixed discriminator makes the relationship's provider match a
    # database invariant.  It is persistence plumbing, not API data.
    host_type: Mapped[HostType] = mapped_column(
        _host_type_enum(create_constraint=False),
        nullable=False,
        default=HostType.DOCKER,
        server_default=text("'docker'"),
    )
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
        ForeignKey("ssh_keypairs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    host_key_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    host_key_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    host_key_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)

    host: Mapped[Host] = relationship(back_populates="docker_details")
    keypair: Mapped[SSHKeypair] = relationship(lazy="joined")


class KubernetesHostDetails(Base):
    """Connection and credential state specific to a Kubernetes host."""

    __tablename__ = "kubernetes_host_details"
    __table_args__ = (
        CheckConstraint(
            "host_type = 'kubernetes'",
            name="ck_kubernetes_host_details_type",
        ),
        ForeignKeyConstraint(
            ("host_id", "host_type"),
            ("hosts.id", "hosts.type"),
            name="fk_kubernetes_host_details_host",
            ondelete="CASCADE",
        ),
    )

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )
    host_type: Mapped[HostType] = mapped_column(
        _host_type_enum(create_constraint=False),
        nullable=False,
        default=HostType.KUBERNETES,
        server_default=text("'kubernetes'"),
    )
    api_url: Mapped[str] = mapped_column(String(512), nullable=False)
    ca_cert_pem: Mapped[str] = mapped_column(Text, nullable=False)
    token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    namespace: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        default="fourdrinier",
        server_default=text("'fourdrinier'"),
    )

    host: Mapped[Host] = relationship(back_populates="kubernetes_details")


class DockerHost(Base):
    """A remote Docker daemon reachable via ``ssh://username@address:port``.

    The ``host_key_*`` columns implement trust-on-first-use: they are NULL
    until the first successful connection records the server's host key, after
    which any mismatch is rejected.
    """

    __tablename__ = "docker_hosts"
    __table_args__ = (Index("ix_docker_hosts_enabled", "enabled"),)

    # Discriminator used by the API's polymorphic read schemas; not a column.
    type: ClassVar[str] = "docker"

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


__all__ = ["DockerHost", "DockerHostDetails", "Host", "KubernetesHostDetails"]
