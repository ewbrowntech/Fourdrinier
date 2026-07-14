"""CRUD helpers for KubernetesHost records."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import KubernetesHost


async def create_host(
    session: AsyncSession,
    *,
    name: str,
    api_url: str,
    ca_cert_pem: str,
    token_encrypted: bytes,
    namespace: str,
    enabled: bool = True,
    labels: dict[str, str] | None = None,
) -> KubernetesHost:
    """Persist a new host. Raises ``IntegrityError`` on duplicate name."""
    host = KubernetesHost(
        name=name,
        api_url=api_url,
        ca_cert_pem=ca_cert_pem,
        token_encrypted=token_encrypted,
        namespace=namespace,
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


async def list_hosts(session: AsyncSession) -> list[KubernetesHost]:
    """Return all hosts ordered by name."""
    stmt: Select[tuple[KubernetesHost]] = select(KubernetesHost).order_by(KubernetesHost.name)
    result: ScalarResult[KubernetesHost] = await session.scalars(stmt)
    return list(result.all())


async def get_host(session: AsyncSession, host_id: uuid.UUID) -> KubernetesHost | None:
    """Return a host by id, or ``None`` if missing."""
    return await session.get(KubernetesHost, host_id)


async def get_host_by_name(session: AsyncSession, name: str) -> KubernetesHost | None:
    """Return a host by name, or ``None`` if missing."""
    stmt: Select[tuple[KubernetesHost]] = select(KubernetesHost).where(KubernetesHost.name == name)
    return await session.scalar(stmt)


async def delete_host(session: AsyncSession, host: KubernetesHost) -> None:
    """Delete a host."""
    await session.delete(host)
    await session.commit()


__all__ = [
    "create_host",
    "delete_host",
    "get_host",
    "get_host_by_name",
    "list_hosts",
]
