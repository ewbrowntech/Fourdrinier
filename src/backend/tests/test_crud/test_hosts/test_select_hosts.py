"""
test_select_hosts.py

Integration tests for the host aggregate selection statement.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts._select_hosts import select_hosts
from fourdrinier.db.models import Host


async def test_select_hosts_001_nominal_provider_details_are_eager_loaded(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
    kubernetes_host_factory: Callable[[str], Host],
) -> None:
    """Test 001 - Nominal
    Condition: Docker and Kubernetes host aggregates exist
    Result: The selection returns both aggregates with provider details eagerly loaded
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    docker_host: Host = docker_host_factory("zulu-docker")
    kubernetes_host: Host = kubernetes_host_factory("alpha-kubernetes")
    async with session_factory() as session:
        session.add_all([docker_host, kubernetes_host])
        await session.commit()
        session.expunge_all()

        # Act
        statement: Select[tuple[Host]] = select_hosts().order_by(Host.name)
        loaded: list[Host] = list((await session.scalars(statement)).all())

    # Assert
    assert [host.name for host in loaded] == ["alpha-kubernetes", "zulu-docker"]
    assert loaded[0].kubernetes_details is not None
    assert loaded[0].kubernetes_details.namespace == "fourdrinier"
    assert loaded[1].docker_details is not None
    assert loaded[1].docker_details.address == "203.0.113.10"
