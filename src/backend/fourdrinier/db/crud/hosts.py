"""CRUD helpers for Host records."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Host, HostKind
from fourdrinier.db.schemas import validate_host_connection

JsonObject = dict[str, Any]


async def create_host(
    session: AsyncSession,
    *,
    name: str,
    kind: HostKind,
    connection: JsonObject,
    enabled: bool = True,
    labels: dict[str, str] | None = None,
) -> Host:
    """Persist a new host. Raises ``IntegrityError`` on duplicate name."""
    normalized: JsonObject = validate_host_connection(kind, connection)
    host_labels: dict[str, str] = labels if labels is not None else {}
    host = Host(
        name=name,
        kind=kind,
        connection=normalized,
        enabled=enabled,
        labels=host_labels,
    )
    session.add(host)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(host)
    return host


async def list_hosts(session: AsyncSession) -> list[Host]:
    """Return all hosts ordered by name."""
    stmt: Select[tuple[Host]] = select(Host).order_by(Host.name)
    result: ScalarResult[Host] = await session.scalars(stmt)
    hosts: list[Host] = list(result.all())
    return hosts


async def get_host(session: AsyncSession, host_id: uuid.UUID) -> Host | None:
    """Return a host by id, or ``None`` if missing."""
    host: Host | None = await session.get(Host, host_id)
    return host


__all__ = ["create_host", "get_host", "list_hosts"]
