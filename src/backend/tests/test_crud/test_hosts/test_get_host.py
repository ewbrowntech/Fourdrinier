"""
test_get_host.py

Integration tests for loading provider-neutral host aggregates by identifier.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts.get_host import get_host
from fourdrinier.db.models import Host
from fourdrinier.hosts.types import HostType


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_get_host_001_nominal_matching_details_are_eager_loaded(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
    kubernetes_host_factory: Callable[[str], Host],
    host_type: HostType,
) -> None:
    """Test 001 - Nominal
    Condition: A host with matching provider details exists for the requested ID
    Result: The host and its matching details remain available after the session closes
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host
    if host_type is HostType.DOCKER:
        host = docker_host_factory("production")
    else:
        host = kubernetes_host_factory("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id
        session.expunge_all()

        # Act
        loaded: Host | None = await get_host(session, host_id)

    # Assert
    assert loaded is not None
    if host_type is HostType.DOCKER:
        assert loaded.docker_details is not None
        assert loaded.docker_details.address == "203.0.113.10"
        assert loaded.kubernetes_details is None
    else:
        assert loaded.kubernetes_details is not None
        assert loaded.kubernetes_details.namespace == "fourdrinier"
        assert loaded.docker_details is None


async def test_get_host_002_anomalous_unknown_host_returns_none(
    app: FastAPI,
) -> None:
    """Test 002 - Anomalous
    Condition: No host exists for the requested ID
    Result: None is returned
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    missing_id: uuid.UUID = uuid.uuid4()

    # Act
    async with session_factory() as session:
        missing: Host | None = await get_host(session, missing_id)

    # Assert
    assert missing is None
