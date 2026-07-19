"""
list_servers.py

List provider-independent logical servers.
"""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def list_servers(session: AsyncSession) -> list[Server]:
    """List logical servers in name order.

    Args:
        session: Session used to query server persistence.

    Returns:
        All logical servers ordered by name.
    """
    statement: Select[tuple[Server]] = select(Server).order_by(Server.name)
    result: ScalarResult[Server] = await session.scalars(statement)
    servers: list[Server] = list(result.all())
    return servers


__all__: list[str] = ["list_servers"]
