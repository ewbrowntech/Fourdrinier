"""Persistence-model tests for the provider-neutral host aggregate."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KeypairSource,
    KubernetesHostDetails,
    SSHKeypair,
)
from fourdrinier.hosts import HostType


def _keypair() -> SSHKeypair:
    return SSHKeypair(
        name="host-key",
        source=KeypairSource.GENERATED,
        algorithm="ed25519",
        public_key="ssh-ed25519 AAAA test",
        fingerprint="SHA256:test",
        private_key_encrypted=b"encrypted",
    )


def _docker_details(keypair: SSHKeypair) -> DockerHostDetails:
    return DockerHostDetails(
        address="203.0.113.10",
        port=22,
        username="docker",
        keypair=keypair,
    )


def test_host_details_relationships_are_owned_one_to_one() -> None:
    mapper = inspect(Host)

    for relationship_name in ("docker_details", "kubernetes_details"):
        relationship = mapper.relationships[relationship_name]
        assert relationship.uselist is False
        assert relationship.single_parent is True
        assert relationship.passive_deletes is True
        assert relationship.cascade.delete
        assert relationship.cascade.delete_orphan


def test_details_foreign_keys_cascade_with_the_parent() -> None:
    for details_model in (DockerHostDetails, KubernetesHostDetails):
        foreign_keys = {
            constraint.name: constraint
            for constraint in details_model.__table__.foreign_key_constraints
        }
        parent_fk = foreign_keys[f"fk_{details_model.__tablename__}_host"]
        assert parent_fk.ondelete == "CASCADE"
        assert [element.target_fullname for element in parent_fk.elements] == [
            "hosts.id",
            "hosts.type",
        ]


async def test_parent_delete_cascades_to_details(
    app,
) -> None:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        keypair = _keypair()
        host = Host(
            type=HostType.DOCKER,
            name="docker",
            docker_details=_docker_details(keypair),
        )
        session.add(host)
        await session.commit()
        host_id = host.id

        # A bulk delete bypasses ORM cascades and therefore proves the
        # database's ON DELETE behavior.
        await session.execute(delete(Host).where(Host.id == host_id))
        await session.commit()

        assert (
            await session.scalar(
                select(DockerHostDetails).where(DockerHostDetails.host_id == host_id)
            )
            is None
        )


async def test_host_name_is_unique_across_provider_types(app) -> None:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        session.add_all(
            [
                Host(type=HostType.DOCKER, name="shared"),
                Host(type=HostType.KUBERNETES, name="shared"),
            ]
        )

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        else:  # pragma: no cover - documents the database invariant
            raise AssertionError("hosts.name accepted a cross-provider duplicate")


async def test_details_must_match_parent_provider(app) -> None:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        host = Host(
            type=HostType.KUBERNETES,
            name="wrong-provider",
            docker_details=_docker_details(_keypair()),
        )
        session.add(host)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        else:  # pragma: no cover - documents the database invariant
            raise AssertionError("Docker details accepted a Kubernetes parent")


async def test_details_cannot_exist_without_parent(app) -> None:
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    async with session_factory() as session:
        orphan = KubernetesHostDetails(
            host_id=uuid4(),
            api_url="https://203.0.113.20:6443",
            ca_cert_pem="certificate",
            token_encrypted=b"encrypted",
        )
        session.add(orphan)

        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        else:  # pragma: no cover - documents the database invariant
            raise AssertionError("orphan Kubernetes details were persisted")
