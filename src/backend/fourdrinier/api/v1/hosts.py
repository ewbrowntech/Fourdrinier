"""
hosts.py

Expose provider-neutral host registration and connectivity endpoints.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, status

from fourdrinier.api.deps import HostServiceDep
from fourdrinier.api.v1.host_responses import host_response, ping_response
from fourdrinier.core.crypto import DecryptionError
from fourdrinier.db.models import Host
from fourdrinier.hosts import (
    HostAuthenticationError,
    HostKeypairNotFoundError,
    HostNameConflictError,
    HostNotFoundError,
    HostPermissionDeniedError,
    HostTrustVerificationError,
    HostType,
    HostTypeChangeError,
    HostUnreachableError,
)
from fourdrinier.hosts.drivers import HostDriverPingResult
from fourdrinier.schemas import HostCreate, HostPingResponse, HostRead, HostUpdate

router: APIRouter = APIRouter(prefix="/hosts", tags=["hosts"])


def _not_found(exc: HostNotFoundError | HostKeypairNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
    )


@router.post("", response_model=HostRead, status_code=status.HTTP_201_CREATED)
async def create_host(body: HostCreate, service: HostServiceDep) -> HostRead:
    try:
        host: Host = await service.create(body)
    except HostKeypairNotFoundError as exc:
        raise _not_found(exc) from exc
    except HostNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return host_response(host)


@router.get("", response_model=list[HostRead])
async def list_hosts(
    service: HostServiceDep,
    type: Literal["docker", "kubernetes"] | None = None,
) -> list[HostRead]:
    host_type: HostType | None = HostType(type) if type is not None else None
    hosts: list[Host] = await service.list(host_type)
    return [host_response(host) for host in hosts]


@router.get("/{host_id}", response_model=HostRead)
async def get_host(host_id: uuid.UUID, service: HostServiceDep) -> HostRead:
    try:
        host: Host = await service.get(host_id)
    except HostNotFoundError as exc:
        raise _not_found(exc) from exc
    return host_response(host)


@router.patch("/{host_id}", response_model=HostRead)
async def update_host(
    host_id: uuid.UUID,
    body: HostUpdate,
    service: HostServiceDep,
) -> HostRead:
    try:
        host: Host = await service.update(host_id, body)
    except (HostNotFoundError, HostKeypairNotFoundError) as exc:
        raise _not_found(exc) from exc
    except (HostNameConflictError, HostTypeChangeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return host_response(host)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: uuid.UUID, service: HostServiceDep) -> None:
    try:
        await service.delete(host_id)
    except HostNotFoundError as exc:
        raise _not_found(exc) from exc


@router.post("/{host_id}/ping", response_model=HostPingResponse)
async def ping_host(host_id: uuid.UUID, service: HostServiceDep) -> HostPingResponse:
    try:
        result: HostDriverPingResult = await service.ping(host_id)
    except HostNotFoundError as exc:
        raise _not_found(exc) from exc
    except HostTrustVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (HostAuthenticationError, HostUnreachableError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except HostPermissionDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except DecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return ping_response(result)


__all__: list[str] = ["router"]
