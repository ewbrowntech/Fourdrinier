"""
update_server.py

Flush changes to a logical server.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def update_server(session: AsyncSession, server: Server) -> Server:
    """Flush changes to a logical server in the current transaction.

    Args:
        session: Session that owns the current transaction.
        server: Attached logical server containing requested changes.

    Returns:
        The flushed server with its update timestamp refreshed.
    """
    await session.flush()
    await session.refresh(server, attribute_names=["updated_at"])
    return server


__all__: list[str] = ["update_server"]
