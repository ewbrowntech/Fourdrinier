"""
delete_server.py

Delete a logical server.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def delete_server(session: AsyncSession, server: Server) -> None:
    """Delete a logical server in the current transaction.

    Args:
        session: Session that owns the current transaction.
        server: Logical server to delete.
    """
    await session.delete(server)
    await session.flush()


__all__: list[str] = ["delete_server"]
