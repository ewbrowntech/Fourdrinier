"""Docker host API — register hosts and validate SSH connectivity."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from fourdrinier.core.crypto import DecryptionError, EncryptionKeyError
from fourdrinier.core.deps import SettingsDep
from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from fourdrinier.db.deps import DbSession
from fourdrinier.db.models import DockerHost
from fourdrinier.db.schemas import (
    DockerHostCreate,
    DockerHostRead,
    PingHostKey,
    PingResponse,
)
from fourdrinier.hosts.docker import service as docker_service
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    HostUnreachableError,
    SSHAuthError,
)

router: APIRouter = APIRouter(prefix="/hosts", tags=["hosts"])


async def _get_host_or_404(session: DbSession, host_id: uuid.UUID) -> DockerHost:
    host: DockerHost | None = await hosts_crud.get_host(session, host_id)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"host {host_id} not found",
        )
    return host


@router.post("", response_model=DockerHostRead, status_code=status.HTTP_201_CREATED)
async def create_host(body: DockerHostCreate, session: DbSession) -> DockerHost:
    if await keypairs_crud.get_keypair(session, body.keypair_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"keypair {body.keypair_id} not found",
        )
    try:
        host: DockerHost = await hosts_crud.create_host(
            session,
            name=body.name,
            address=body.address,
            port=body.port,
            username=body.username,
            keypair_id=body.keypair_id,
            enabled=body.enabled,
            labels=body.labels,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"host with name {body.name!r} already exists",
        ) from exc
    return host


@router.get("", response_model=list[DockerHostRead])
async def list_hosts(session: DbSession) -> list[DockerHost]:
    return await hosts_crud.list_hosts(session)


@router.get("/{host_id}", response_model=DockerHostRead)
async def get_host(host_id: uuid.UUID, session: DbSession) -> DockerHost:
    return await _get_host_or_404(session, host_id)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: uuid.UUID, session: DbSession) -> None:
    host: DockerHost = await _get_host_or_404(session, host_id)
    await hosts_crud.delete_host(session, host)


@router.post("/{host_id}/ping", response_model=PingResponse)
async def ping_host(
    host_id: uuid.UUID, session: DbSession, settings: SettingsDep
) -> PingResponse:
    host: DockerHost = await _get_host_or_404(session, host_id)
    try:
        result: docker_service.PingResult = await docker_service.ping_host(
            session, host, settings
        )
    except HostKeyMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except SSHAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except HostUnreachableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except (EncryptionKeyError, DecryptionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return PingResponse(
        latency_ms=result.latency_ms,
        docker_version=result.docker_version,
        api_version=result.api_version,
        os=result.os,
        arch=result.arch,
        host_key=PingHostKey(
            fingerprint=result.host_key.fingerprint,
            key_type=result.host_key.key_type,
            first_seen=result.host_key.first_seen,
        ),
    )


__all__ = ["router"]
