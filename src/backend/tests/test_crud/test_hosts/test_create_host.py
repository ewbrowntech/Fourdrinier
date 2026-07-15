"""
test_create_host.py

Integration tests for creating provider-neutral host aggregates.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts.create_host import create_host
from fourdrinier.db.models import DockerHostDetails, Host, KubernetesHostDetails
from fourdrinier.hosts.types import HostType


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_create_host_001_nominal_complete_aggregate_is_persisted(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
    kubernetes_host_factory: Callable[[str], Host],
    host_type: HostType,
) -> None:
    """Test 001 - Nominal
    Condition: A parent host has provider details matching its type
    Result: The parent and matching details are persisted in the caller's transaction
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host
    if host_type is HostType.DOCKER:
        host = docker_host_factory("production")
    else:
        host = kubernetes_host_factory("production")

    # Act
    async with session_factory() as session:
        created: Host = await create_host(session, host)
        await session.commit()
        host_id: uuid.UUID = created.id

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host_id)
        docker_details: DockerHostDetails | None = await session.get(DockerHostDetails, host_id)
        kubernetes_details: KubernetesHostDetails | None = await session.get(
            KubernetesHostDetails,
            host_id,
        )
    assert persisted is not None
    assert persisted.type is host_type
    assert persisted.created_at is not None
    assert (docker_details is not None) is (host_type is HostType.DOCKER)
    assert (kubernetes_details is not None) is (host_type is HostType.KUBERNETES)


async def test_create_host_002_anomalous_details_failure_is_atomic(
    app: FastAPI,
) -> None:
    """Test 002 - Anomalous
    Condition: Docker details reference a keypair that does not exist
    Result: IntegrityError leaves no parent row after the caller rolls back
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    missing_keypair_id: uuid.UUID = uuid.uuid4()
    host: Host = Host(
        type=HostType.DOCKER,
        name="invalid-docker",
        docker_details=DockerHostDetails(
            address="203.0.113.10",
            port=22,
            username="docker",
            keypair_id=missing_keypair_id,
        ),
    )

    # Act
    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            await create_host(session, host)
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host.id)
        details: DockerHostDetails | None = await session.get(DockerHostDetails, host.id)
    assert persisted is None
    assert details is None
