"""
docker_hosts.py

Provide persistence helpers for the legacy Docker host model during migration.
"""

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
    """Persist a host using the legacy Docker-only table.

    Args:
        session: Session used to persist the host.
        name: Globally unique host name.
        address: Network address used for the SSH connection.
        port: SSH port exposed by the host.
        username: Account used for the SSH connection.
        keypair_id: Identifier of the SSH keypair used for authentication.
        enabled: Whether Fourdrinier may schedule work on the host.
        labels: Optional user-defined host labels.

    Returns:
        The committed and refreshed legacy Docker host.

    Raises:
        IntegrityError: If the host violates a database constraint.
    """
    host: DockerHost = DockerHost(
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
    """List legacy Docker hosts in name order.

    Args:
        session: Session used to query hosts.

    Returns:
        Legacy Docker hosts ordered by name.
    """
    stmt: Select[tuple[DockerHost]] = select(DockerHost).order_by(DockerHost.name)
    result: ScalarResult[DockerHost] = await session.scalars(stmt)
    hosts: list[DockerHost] = list(result.all())
    return hosts


async def get_host(session: AsyncSession, host_id: uuid.UUID) -> DockerHost | None:
    """Load a legacy Docker host by ID.

    Args:
        session: Session used to query hosts.
        host_id: Identifier of the requested host.

    Returns:
        The matching host, or ``None`` when it does not exist.
    """
    host: DockerHost | None = await session.get(DockerHost, host_id)
    return host


async def delete_host(session: AsyncSession, host: DockerHost) -> None:
    """Delete a legacy Docker host and commit the transaction.

    Args:
        session: Session that owns the delete transaction.
        host: Legacy Docker host to delete.
    """
    await session.delete(host)
    await session.commit()


__all__: list[str] = [
    "create_host",
    "delete_host",
    "get_host",
    "list_hosts",
]
