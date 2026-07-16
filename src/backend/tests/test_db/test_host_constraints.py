"""
test_host_constraints.py

Integration tests for provider-neutral host database constraints.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KeypairSource,
    KubernetesHostDetails,
    SSHKeypair,
)
from fourdrinier.hosts.types import HostType


def _docker_host(name: str, host_type: HostType) -> Host:
    keypair: SSHKeypair = SSHKeypair(
        name=f"{name}-key",
        source=KeypairSource.GENERATED,
        algorithm="ed25519",
        public_key=f"ssh-ed25519 AAAA {name}",
        fingerprint=f"SHA256:{name}",
        private_key_encrypted=b"encrypted",
    )
    details: DockerHostDetails = DockerHostDetails(
        address="203.0.113.10",
        port=22,
        username="docker",
        keypair=keypair,
    )
    host: Host = Host(
        type=host_type,
        name=name,
        docker_details=details,
    )
    return host


async def test_host_constraints_001_nominal_parent_delete_cascades_to_details(
    app: FastAPI,
) -> None:
    """Test 001 - Nominal
    Condition: A host parent is deleted directly without using ORM relationship cascades
    Result: The database deletes its owned provider details
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = _docker_host("docker", HostType.DOCKER)
    session: AsyncSession
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id

        # Act
        await session.execute(delete(Host).where(Host.id == host_id))
        await session.commit()

    # Assert
    async with session_factory() as session:
        details: DockerHostDetails | None = await session.get(DockerHostDetails, host_id)
    assert details is None


async def test_host_constraints_002_anomalous_details_do_not_match_parent_provider(
    app: FastAPI,
) -> None:
    """Test 002 - Anomalous
    Condition: A Kubernetes parent is assigned Docker provider details
    Result: IntegrityError is raised and the aggregate is not persisted
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = _docker_host("wrong-provider", HostType.KUBERNETES)
    session: AsyncSession

    # Act
    async with session_factory() as session:
        session.add(host)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host.id)
    assert persisted is None


async def test_host_constraints_003_anomalous_details_do_not_have_parent(
    app: FastAPI,
) -> None:
    """Test 003 - Anomalous
    Condition: Kubernetes provider details reference a host that does not exist
    Result: IntegrityError is raised and the details are not persisted
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    missing_host_id: uuid.UUID = uuid.uuid4()
    orphan: KubernetesHostDetails = KubernetesHostDetails(
        host_id=missing_host_id,
        api_url="https://203.0.113.20:6443",
        ca_cert_pem="certificate",
        token_encrypted=b"encrypted",
    )
    session: AsyncSession

    # Act
    async with session_factory() as session:
        session.add(orphan)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: KubernetesHostDetails | None = await session.get(
            KubernetesHostDetails,
            missing_host_id,
        )
    assert persisted is None
