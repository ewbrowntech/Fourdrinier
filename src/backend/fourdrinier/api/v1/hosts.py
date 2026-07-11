"""Host API — create and read configurable runtime hosts."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.deps import DbSession
from fourdrinier.db.models import Host
from fourdrinier.db.schemas import HostCreate, HostRead

router: APIRouter = APIRouter(prefix="/hosts", tags=["hosts"])


@router.post("", response_model=HostRead, status_code=status.HTTP_201_CREATED)
async def create_host(body: HostCreate, session: DbSession) -> Host:
    try:
        host: Host = await hosts_crud.create_host(
            session,
            name=body.name,
            kind=body.kind,
            connection=body.connection_payload(),
            enabled=body.enabled,
            labels=body.labels,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"host with name {body.name!r} already exists",
        ) from exc
    return host


@router.get("", response_model=list[HostRead])
async def list_hosts(session: DbSession) -> list[Host]:
    hosts: list[Host] = await hosts_crud.list_hosts(session)
    return hosts


@router.get("/{host_id}", response_model=HostRead)
async def get_host(host_id: uuid.UUID, session: DbSession) -> Host:
    host: Host | None = await hosts_crud.get_host(session, host_id)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"host {host_id} not found",
        )
    return host


__all__ = ["router"]
