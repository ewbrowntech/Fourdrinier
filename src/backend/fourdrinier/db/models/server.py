"""
server.py

Define the provider-independent logical server ORM model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from fourdrinier.db.base import Base
from fourdrinier.servers.types import (
    DEFAULT_SERVER_CPU_MILLICORES,
    DEFAULT_SERVER_MEMORY_BYTES,
    ServerDesiredState,
    ServerRuntime,
)


def _enum_values(enum_cls: type[ServerRuntime] | type[ServerDesiredState]) -> list[str]:
    return [member.value for member in enum_cls]


class Server(Base):
    """Persist desired Minecraft configuration independently of any host."""

    __tablename__ = "servers"
    __table_args__ = (
        UniqueConstraint("name", name="uq_servers_name"),
        CheckConstraint(
            "cpu_millicores > 0",
            name="ck_servers_cpu_millicores_positive",
        ),
        CheckConstraint(
            "memory_bytes > 0",
            name="ck_servers_memory_bytes_positive",
        ),
        CheckConstraint("spec_generation >= 1", name="ck_servers_spec_generation_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    runtime: Mapped[ServerRuntime] = mapped_column(
        Enum(
            ServerRuntime,
            name="server_runtime",
            native_enum=False,
            values_callable=_enum_values,
            create_constraint=True,
            validate_strings=True,
            length=16,
        ),
        nullable=False,
        default=ServerRuntime.PUMPKIN,
        server_default=text("'pumpkin'"),
    )
    minecraft_version: Mapped[str] = mapped_column(String(32), nullable=False)
    cpu_millicores: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_SERVER_CPU_MILLICORES,
        server_default=text(str(DEFAULT_SERVER_CPU_MILLICORES)),
    )
    memory_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=DEFAULT_SERVER_MEMORY_BYTES,
        server_default=text(str(DEFAULT_SERVER_MEMORY_BYTES)),
    )
    desired_state: Mapped[ServerDesiredState] = mapped_column(
        Enum(
            ServerDesiredState,
            name="server_desired_state",
            native_enum=False,
            values_callable=_enum_values,
            create_constraint=True,
            validate_strings=True,
            length=16,
        ),
        nullable=False,
        default=ServerDesiredState.STOPPED,
        server_default=text("'stopped'"),
    )
    spec_generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
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


__all__: list[str] = ["Server"]
