"""KubernetesHost ORM model — clusters reached over HTTPS with a bearer token."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    LargeBinary,
    String,
    Text,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from fourdrinier.db.base import Base


class KubernetesHost(Base):
    """A Kubernetes API server reachable at ``api_url``.

    Authentication uses a ServiceAccount bearer token (stored encrypted) and
    the cluster CA certificate (public material, stored as plaintext PEM) for
    TLS verification. Operations are scoped to ``namespace``.
    """

    __tablename__ = "kubernetes_hosts"
    __table_args__ = (Index("ix_kubernetes_hosts_enabled", "enabled"),)

    # Discriminator used by the API's polymorphic read schemas; not a column.
    type: ClassVar[str] = "kubernetes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    api_url: Mapped[str] = mapped_column(String(512), nullable=False)
    ca_cert_pem: Mapped[str] = mapped_column(Text, nullable=False)
    token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    namespace: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        default="fourdrinier",
        server_default=text("'fourdrinier'"),
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


__all__ = ["KubernetesHost"]
