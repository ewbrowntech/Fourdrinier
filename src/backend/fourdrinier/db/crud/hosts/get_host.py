"""
get_host.py

Load a provider-neutral host aggregate by identifier.
"""

from __future__ import annotations

from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.crud.hosts._select_hosts import select_hosts
from fourdrinier.db.models import Host
from fourdrinier.hosts.types import HostId


async def get_host(session: AsyncSession, host_id: HostId) -> Host | None:
    """Load a host and its provider details by ID.

    Args:
        session: Session used to query host persistence.
        host_id: Provider-neutral host identifier.

    Returns:
        The eagerly loaded host aggregate, or ``None`` when it does not exist.
    """
    statement: Select[tuple[Host]] = select_hosts().where(Host.id == host_id)
    host: Host | None = await session.scalar(statement)
    return host


__all__: list[str] = ["get_host"]
