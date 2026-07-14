"""CRUD helpers for SSHKeypair records."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import DockerHost, KeypairSource, SSHKeypair


class KeypairInUseError(RuntimeError):
    """Keypair is referenced by one or more hosts and cannot be deleted."""


async def create_keypair(
    session: AsyncSession,
    *,
    name: str,
    source: KeypairSource,
    algorithm: str,
    public_key: str,
    fingerprint: str,
    private_key_encrypted: bytes,
) -> SSHKeypair:
    """Persist a new keypair. Raises ``IntegrityError`` on duplicate name/fingerprint."""
    keypair = SSHKeypair(
        name=name,
        source=source,
        algorithm=algorithm,
        public_key=public_key,
        fingerprint=fingerprint,
        private_key_encrypted=private_key_encrypted,
    )
    session.add(keypair)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise
    await session.refresh(keypair)
    return keypair


async def list_keypairs(session: AsyncSession) -> list[SSHKeypair]:
    """Return all keypairs ordered by name."""
    stmt: Select[tuple[SSHKeypair]] = select(SSHKeypair).order_by(SSHKeypair.name)
    result: ScalarResult[SSHKeypair] = await session.scalars(stmt)
    return list(result.all())


async def get_keypair(session: AsyncSession, keypair_id: uuid.UUID) -> SSHKeypair | None:
    """Return a keypair by id, or ``None`` if missing."""
    return await session.get(SSHKeypair, keypair_id)


async def delete_keypair(session: AsyncSession, keypair: SSHKeypair) -> None:
    """Delete a keypair. Raises ``KeypairInUseError`` if any host references it."""
    stmt = select(func.count()).select_from(DockerHost).where(DockerHost.keypair_id == keypair.id)
    referencing_hosts: int = (await session.execute(stmt)).scalar_one()
    if referencing_hosts:
        raise KeypairInUseError(f"keypair {keypair.name!r} is used by {referencing_hosts} host(s)")
    await session.delete(keypair)
    await session.commit()


__all__ = [
    "KeypairInUseError",
    "create_keypair",
    "delete_keypair",
    "get_keypair",
    "list_keypairs",
]
