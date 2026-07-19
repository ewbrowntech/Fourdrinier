"""
create_host.py

Persist a complete provider-neutral host aggregate.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Host


async def create_host(session: AsyncSession, host: Host) -> Host:
    """Add a complete host aggregate to the current transaction.

    Args:
        session: Session that owns the current transaction.
        host: Parent host with its matching provider details attached.

    Returns:
        The flushed aggregate, including database-generated values.
    """
    session.add(host)
    await session.flush()
    return host


__all__: list[str] = ["create_host"]
