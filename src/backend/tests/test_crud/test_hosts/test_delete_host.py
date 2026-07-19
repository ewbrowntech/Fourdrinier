"""
test_delete_host.py

Integration tests for deleting provider-neutral host aggregates.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts.delete_host import delete_host
from fourdrinier.db.models import Host, KubernetesHostDetails


async def test_delete_host_001_nominal_parent_and_details_are_deleted(
    app: FastAPI,
    kubernetes_host_factory: Callable[[str], Host],
) -> None:
    """Test 001 - Nominal
    Condition: A persisted Kubernetes host aggregate is deleted and the caller commits
    Result: The parent and owned details rows are both removed
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = kubernetes_host_factory("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id

        # Act
        await delete_host(session, host)
        await session.commit()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host_id)
        details: KubernetesHostDetails | None = await session.get(
            KubernetesHostDetails,
            host_id,
        )
    assert persisted is None
    assert details is None


async def test_delete_host_002_nominal_caller_can_roll_back_delete(
    app: FastAPI,
    kubernetes_host_factory: Callable[[str], Host],
) -> None:
    """Test 002 - Nominal
    Condition: A host deletion is flushed and the caller rolls the transaction back
    Result: The parent and details remain persisted
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = kubernetes_host_factory("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id

        # Act
        await delete_host(session, host)
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host_id)
        details: KubernetesHostDetails | None = await session.get(
            KubernetesHostDetails,
            host_id,
        )
    assert persisted is not None
    assert details is not None
