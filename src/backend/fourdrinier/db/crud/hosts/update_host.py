"""
update_host.py

Flush changes to an existing provider-neutral host aggregate.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Host


async def update_host(session: AsyncSession, host: Host) -> Host:
    """Flush changes to a host aggregate in the current transaction.

    Args:
        session: Session that owns the current transaction.
        host: Attached host aggregate containing the requested changes.

    Returns:
        The flushed aggregate with its update timestamp refreshed.
    """
    await session.flush()
    await session.refresh(host, attribute_names=["updated_at"])
    return host


__all__: list[str] = ["update_host"]
