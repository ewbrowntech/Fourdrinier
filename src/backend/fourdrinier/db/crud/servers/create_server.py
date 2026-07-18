"""
create_server.py

Persist a provider-independent logical server.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def create_server(session: AsyncSession, server: Server) -> Server:
    """Add a logical server to the current transaction.

    Args:
        session: Session that owns the current transaction.
        server: Logical server to persist.

    Returns:
        The flushed server, including database-generated values.
    """
    session.add(server)
    await session.flush()
    return server


__all__: list[str] = ["create_server"]
