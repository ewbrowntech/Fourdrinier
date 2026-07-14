"""
hosts.py

Persist and retrieve provider-neutral host aggregates.
"""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from fourdrinier.db.models import Host
from fourdrinier.hosts.types import HostId, HostType


def _hosts_statement() -> Select[tuple[Host]]:
    statement: Select[tuple[Host]] = select(Host).options(
        selectinload(Host.docker_details),
        selectinload(Host.kubernetes_details),
    )
    return statement


class HostRepository:
    """Persist host aggregates without owning their transaction boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self._session: AsyncSession = session

    async def create(self, host: Host) -> Host:
        """Add a complete host aggregate to the current transaction.

        Args:
            host: Parent host with its matching provider details attached.

        Returns:
            The flushed host aggregate, including database-generated values.
        """
        self._session.add(host)
        await self._session.flush()
        return host

    async def get_by_id(self, host_id: HostId) -> Host | None:
        """Load a host and its provider details by ID.

        Args:
            host_id: Provider-neutral host identifier.

        Returns:
            The eagerly loaded host aggregate, or ``None`` when it does not exist.
        """
        statement: Select[tuple[Host]] = _hosts_statement().where(Host.id == host_id)
        host: Host | None = await self._session.scalar(statement)
        return host

    async def get_by_name(self, name: str) -> Host | None:
        """Load a host and its provider details by its globally unique name.

        Args:
            name: Human-readable host name.

        Returns:
            The eagerly loaded host aggregate, or ``None`` when it does not exist.
        """
        statement: Select[tuple[Host]] = _hosts_statement().where(Host.name == name)
        host: Host | None = await self._session.scalar(statement)
        return host

    async def list(self, host_type: HostType | None = None) -> list[Host]:
        """List host aggregates in name order, optionally filtered by provider.

        Args:
            host_type: Provider type to include, or ``None`` to include every type.

        Returns:
            Eagerly loaded host aggregates ordered by name.
        """
        statement: Select[tuple[Host]] = _hosts_statement()
        if host_type is not None:
            statement = statement.where(Host.type == host_type)
        statement = statement.order_by(Host.name)
        result: ScalarResult[Host] = await self._session.scalars(statement)
        hosts: list[Host] = list(result.all())
        return hosts

    async def delete(self, host: Host) -> None:
        """Delete a host aggregate in the current transaction.

        Args:
            host: Host aggregate to delete with its provider details.
        """
        await self._session.delete(host)
        await self._session.flush()


__all__: list[str] = ["HostRepository"]
