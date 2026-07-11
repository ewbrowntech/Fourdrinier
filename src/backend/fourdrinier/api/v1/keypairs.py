"""SSH keypair API — generate or import keypairs for Docker hosts."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from fourdrinier.core.crypto import EncryptionKeyError, encrypt_secret
from fourdrinier.core.deps import SettingsDep
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from fourdrinier.db.crud.ssh_keypairs import KeypairInUseError
from fourdrinier.db.deps import DbSession
from fourdrinier.db.models import KeypairSource, SSHKeypair
from fourdrinier.db.schemas import KeypairCreate, KeypairRead
from fourdrinier.hosts.ssh.keys import (
    KeypairMaterial,
    PrivateKeyError,
    generate_keypair,
    import_private_key,
)

router: APIRouter = APIRouter(prefix="/keypairs", tags=["keypairs"])


@router.post("", response_model=KeypairRead, status_code=status.HTTP_201_CREATED)
async def create_keypair(
    body: KeypairCreate, session: DbSession, settings: SettingsDep
) -> SSHKeypair:
    if body.private_key is not None:
        try:
            material: KeypairMaterial = import_private_key(body.private_key)
        except PrivateKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(exc),
            ) from exc
        source = KeypairSource.UPLOADED
    else:
        material = generate_keypair()
        source = KeypairSource.GENERATED

    try:
        encrypted: bytes = encrypt_secret(material.private_key_pem.encode(), settings)
    except EncryptionKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    try:
        keypair: SSHKeypair = await keypairs_crud.create_keypair(
            session,
            name=body.name,
            source=source,
            algorithm=material.algorithm,
            public_key=material.public_key,
            fingerprint=material.fingerprint,
            private_key_encrypted=encrypted,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"keypair with name {body.name!r} or the same fingerprint already exists",
        ) from exc
    return keypair


@router.get("", response_model=list[KeypairRead])
async def list_keypairs(session: DbSession) -> list[SSHKeypair]:
    return await keypairs_crud.list_keypairs(session)


@router.get("/{keypair_id}", response_model=KeypairRead)
async def get_keypair(keypair_id: uuid.UUID, session: DbSession) -> SSHKeypair:
    keypair: SSHKeypair | None = await keypairs_crud.get_keypair(session, keypair_id)
    if keypair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"keypair {keypair_id} not found",
        )
    return keypair


@router.delete("/{keypair_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keypair(keypair_id: uuid.UUID, session: DbSession) -> None:
    keypair: SSHKeypair | None = await keypairs_crud.get_keypair(session, keypair_id)
    if keypair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"keypair {keypair_id} not found",
        )
    try:
        await keypairs_crud.delete_keypair(session, keypair)
    except KeypairInUseError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


__all__ = ["router"]
