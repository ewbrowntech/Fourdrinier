"""
list_hosts.py

List provider-neutral host aggregates with optional provider filtering.
"""

from __future__ import annotations

from sqlalchemy import Select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.crud.hosts._select_hosts import select_hosts
from fourdrinier.db.models import Host
from fourdrinier.hosts.types import HostType


async def list_hosts(
    session: AsyncSession,
    host_type: HostType | None = None,
) -> list[Host]:
    """List host aggregates in name order with an optional provider filter.

    Args:
        session: Session used to query host persistence.
        host_type: Provider type to include, or ``None`` to include every type.

    Returns:
        Eagerly loaded host aggregates ordered by name.
    """
    statement: Select[tuple[Host]] = select_hosts()
    if host_type is not None:
        statement = statement.where(Host.type == host_type)
    statement = statement.order_by(Host.name)
    result: ScalarResult[Host] = await session.scalars(statement)
    hosts: list[Host] = list(result.all())
    return hosts


__all__: list[str] = ["list_hosts"]
