"""
delete_host.py

Delete a provider-neutral host aggregate.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Host


async def delete_host(session: AsyncSession, host: Host) -> None:
    """Delete a host aggregate in the current transaction.

    Args:
        session: Session that owns the current transaction.
        host: Host aggregate to delete with its provider details.
    """
    await session.delete(host)
    await session.flush()


__all__: list[str] = ["delete_host"]
