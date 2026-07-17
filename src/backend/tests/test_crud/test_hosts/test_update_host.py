"""
test_update_host.py

Integration tests for flushing updates to provider-neutral host aggregates.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts.update_host import update_host
from fourdrinier.db.models import Host


async def test_update_host_001_nominal_changes_are_flushed_and_returned(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
) -> None:
    """Test 001 - Nominal
    Condition: An attached host aggregate contains parent and provider-detail changes
    Result: The flushed aggregate and committed rows contain all changes
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = docker_host_factory("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host.name = "staging"
        assert host.docker_details is not None
        host.docker_details.port = 2222

        # Act
        result: Host = await update_host(session, host)
        await session.commit()

    # Assert
    assert result is host
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host.id)
        assert persisted is not None
        await session.refresh(persisted, attribute_names=["docker_details"])
    assert persisted.name == "staging"
    assert persisted.docker_details is not None
    assert persisted.docker_details.port == 2222


async def test_update_host_002_nominal_caller_can_roll_back_changes(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
) -> None:
    """Test 002 - Nominal
    Condition: A host update is flushed and the caller rolls the transaction back
    Result: The original persisted values remain unchanged
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = docker_host_factory("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id
        host.name = "discarded"

        # Act
        await update_host(session, host)
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host_id)
    assert persisted is not None
    assert persisted.name == "production"
