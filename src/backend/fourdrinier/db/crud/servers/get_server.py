"""
get_server.py

Load a logical server by identifier.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server
from fourdrinier.servers.types import ServerId


async def get_server(session: AsyncSession, server_id: ServerId) -> Server | None:
    """Load a logical server by ID.

    Args:
        session: Session used to query server persistence.
        server_id: Logical server identifier.

    Returns:
        The matching server, or ``None`` when it does not exist.
    """
    server: Server | None = await session.get(Server, server_id)
    return server


__all__: list[str] = ["get_server"]
