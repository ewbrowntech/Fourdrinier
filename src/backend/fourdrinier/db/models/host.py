"""Host ORM model — Docker or Kubernetes runtime targets."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, Index, String, Uuid, func, text, true
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from fourdrinier.db.base import Base

JsonObject = dict[str, Any]


class HostKind(str, enum.Enum):
    """Runtime target kind."""

    DOCKER = "docker"
    KUBERNETES = "kubernetes"


def _host_kind_values(enum_cls: type[HostKind]) -> list[str]:
    return [member.value for member in enum_cls]


class Host(Base):
    """A configurable runtime host (Docker daemon or Kubernetes cluster)."""

    __tablename__ = "hosts"
    __table_args__ = (
        Index("ix_hosts_kind", "kind"),
        Index("ix_hosts_enabled", "enabled"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    kind: Mapped[HostKind] = mapped_column(
        Enum(
            HostKind,
            name="host_kind",
            native_enum=False,
            values_callable=_host_kind_values,
            length=32,
        ),
        nullable=False,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=true(),
        default=True,
    )
    connection: Mapped[JsonObject] = mapped_column(JSON, nullable=False)
    labels: Mapped[dict[str, str]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default=text("'{}'"),
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


__all__ = ["Host", "HostKind"]
