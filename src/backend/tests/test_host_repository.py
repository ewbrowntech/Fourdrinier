"""
test_host_repository.py

Integration tests for the provider-neutral host persistence repository.
"""

from __future__ import annotations

import uuid
from typing import Literal

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KeypairSource,
    KubernetesHostDetails,
    SSHKeypair,
)
from fourdrinier.db.repositories import HostRepository
from fourdrinier.hosts.types import HostType


def _keypair(name: str = "host-key") -> SSHKeypair:
    keypair: SSHKeypair = SSHKeypair(
        name=name,
        source=KeypairSource.GENERATED,
        algorithm="ed25519",
        public_key=f"ssh-ed25519 AAAA {name}",
        fingerprint=f"SHA256:{name}",
        private_key_encrypted=b"encrypted",
    )
    return keypair


def _docker_host(name: str, keypair: SSHKeypair) -> Host:
    host: Host = Host(
        type=HostType.DOCKER,
        name=name,
        labels={"provider": "docker"},
        docker_details=DockerHostDetails(
            address="203.0.113.10",
            port=22,
            username="docker",
            keypair=keypair,
        ),
    )
    return host


def _kubernetes_host(name: str) -> Host:
    host: Host = Host(
        type=HostType.KUBERNETES,
        name=name,
        labels={"provider": "kubernetes"},
        kubernetes_details=KubernetesHostDetails(
            api_url="https://203.0.113.20:6443",
            ca_cert_pem="certificate",
            token_encrypted=b"encrypted-token",
            namespace="fourdrinier",
        ),
    )
    return host


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_host_repository_create_001_nominal_complete_aggregate_is_persisted(
    app: FastAPI,
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
        host = _docker_host("production", _keypair())
    else:
        host = _kubernetes_host("production")

    # Act
    async with session_factory() as session:
        repository: HostRepository = HostRepository(session)
        created: Host = await repository.create(host)
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


async def test_host_repository_create_002_anomalous_details_failure_is_atomic(
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
        repository: HostRepository = HostRepository(session)
        with pytest.raises(IntegrityError):
            await repository.create(host)
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Host | None = await session.get(Host, host.id)
        details: DockerHostDetails | None = await session.get(DockerHostDetails, host.id)
    assert persisted is None
    assert details is None


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_host_repository_get_by_id_003_nominal_matching_details_are_eager_loaded(
    app: FastAPI,
    host_type: HostType,
) -> None:
    """Test 003 - Nominal
    Condition: A host with matching provider details exists for the requested ID
    Result: The host and its matching details remain available after the session closes
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host
    if host_type is HostType.DOCKER:
        host = _docker_host("production", _keypair())
    else:
        host = _kubernetes_host("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id
        session.expunge_all()

        # Act
        repository: HostRepository = HostRepository(session)
        loaded: Host | None = await repository.get_by_id(host_id)

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


async def test_host_repository_get_by_name_004_nominal_matching_host_is_returned(
    app: FastAPI,
) -> None:
    """Test 004 - Nominal
    Condition: A Kubernetes host exists with the globally unique requested name
    Result: The matching host and Kubernetes details are returned
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = _kubernetes_host("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        session.expunge_all()

        # Act
        repository: HostRepository = HostRepository(session)
        loaded: Host | None = await repository.get_by_name("production")

    # Assert
    assert loaded is not None
    assert loaded.id == host.id
    assert loaded.kubernetes_details is not None
    assert loaded.kubernetes_details.api_url == "https://203.0.113.20:6443"


@pytest.mark.parametrize("lookup", ["id", "name"])
async def test_host_repository_lookup_005_anomalous_unknown_host_returns_none(
    app: FastAPI,
    lookup: Literal["id", "name"],
) -> None:
    """Test 005 - Anomalous
    Condition: No host exists for the requested ID or name
    Result: The selected lookup returns None
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    missing_id: uuid.UUID = uuid.uuid4()

    # Act
    async with session_factory() as session:
        repository: HostRepository = HostRepository(session)
        missing: Host | None
        if lookup == "id":
            missing = await repository.get_by_id(missing_id)
        else:
            missing = await repository.get_by_name("missing")

    # Assert
    assert missing is None


@pytest.mark.parametrize(
    ("host_type", "expected_names"),
    [
        pytest.param(None, ["alpha-kubernetes", "zulu-docker"], id="all"),
        pytest.param(HostType.DOCKER, ["zulu-docker"], id="docker"),
        pytest.param(HostType.KUBERNETES, ["alpha-kubernetes"], id="kubernetes"),
    ],
)
async def test_host_repository_list_006_nominal_hosts_are_ordered_and_filtered(
    app: FastAPI,
    host_type: HostType | None,
    expected_names: list[str],
) -> None:
    """Test 006 - Nominal
    Condition: Docker and Kubernetes hosts exist and an optional provider filter is supplied
    Result: Matching hosts are returned in deterministic name order with details loaded
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    docker_host: Host = _docker_host("zulu-docker", _keypair())
    kubernetes_host: Host = _kubernetes_host("alpha-kubernetes")
    async with session_factory() as session:
        session.add_all([docker_host, kubernetes_host])
        await session.commit()
        session.expunge_all()

        # Act
        repository: HostRepository = HostRepository(session)
        loaded: list[Host] = await repository.list(host_type)

    # Assert
    assert [host.name for host in loaded] == expected_names
    for host in loaded:
        if host.type is HostType.DOCKER:
            assert host.docker_details is not None
        else:
            assert host.kubernetes_details is not None


async def test_host_repository_delete_007_nominal_parent_and_details_are_deleted(
    app: FastAPI,
) -> None:
    """Test 007 - Nominal
    Condition: A persisted Kubernetes host aggregate is deleted and the caller commits
    Result: The parent and owned details rows are both removed
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = _kubernetes_host("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id

        # Act
        repository: HostRepository = HostRepository(session)
        await repository.delete(host)
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


async def test_host_repository_delete_008_nominal_caller_can_roll_back_delete(
    app: FastAPI,
) -> None:
    """Test 008 - Nominal
    Condition: A host deletion is flushed and the caller rolls the transaction back
    Result: The parent and details remain persisted
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    host: Host = _kubernetes_host("production")
    async with session_factory() as session:
        session.add(host)
        await session.commit()
        host_id: uuid.UUID = host.id

        # Act
        repository: HostRepository = HostRepository(session)
        await repository.delete(host)
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
