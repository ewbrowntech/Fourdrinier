"""CRUD helpers for DockerHost records."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import DockerHost


async def create_host(
    session: AsyncSession,
    *,
    name: str,
    address: str,
    port: int,
    username: str,
    keypair_id: uuid.UUID,
    enabled: bool = True,
    labels: dict[str, str] | None = None,
) -> DockerHost:
    """Persist a new host. Raises ``IntegrityError`` on duplicate name."""
    host = DockerHost(
        name=name,
        address=address,
        port=port,
        username=username,
        keypair_id=keypair_id,
        enabled=enabled,
        labels=labels if labels is not None else {},
    )
    session.add(host)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(host)
    return host


async def list_hosts(session: AsyncSession) -> list[DockerHost]:
    """Return all hosts ordered by name."""
    stmt: Select[tuple[DockerHost]] = select(DockerHost).order_by(DockerHost.name)
    result: ScalarResult[DockerHost] = await session.scalars(stmt)
    return list(result.all())


async def get_host(session: AsyncSession, host_id: uuid.UUID) -> DockerHost | None:
    """Return a host by id, or ``None`` if missing."""
    return await session.get(DockerHost, host_id)


async def get_host_by_name(session: AsyncSession, name: str) -> DockerHost | None:
    """Return a host by name, or ``None`` if missing."""
    stmt: Select[tuple[DockerHost]] = select(DockerHost).where(DockerHost.name == name)
    return await session.scalar(stmt)


async def delete_host(session: AsyncSession, host: DockerHost) -> None:
    """Delete a host."""
    await session.delete(host)
    await session.commit()


__all__ = ["create_host", "delete_host", "get_host", "get_host_by_name", "list_hosts"]
