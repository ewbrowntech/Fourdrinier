"""Host API — register Docker and Kubernetes hosts and validate connectivity."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, status

from fourdrinier.core.crypto import DecryptionError, EncryptionKeyError, FernetSecretCipher
from fourdrinier.core.deps import SettingsDep
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from fourdrinier.db.deps import DbSession
from fourdrinier.db.models import DockerHostDetails, Host, KubernetesHostDetails
from fourdrinier.db.schemas import (
    DockerHostCreate,
    DockerHostRead,
    DockerPingResponse,
    HostCreate,
    HostListResponse,
    HostPingResponse,
    HostRead,
    KubernetesHostRead,
    KubernetesPingResponse,
    PingHostKey,
)
from fourdrinier.hosts import (
    HostAuthenticationError,
    HostNameConflictError,
    HostNotFoundError,
    HostPermissionDeniedError,
    HostPingResult,
    HostTrustVerificationError,
    HostType,
    HostUnreachableError,
)
from fourdrinier.hosts.docker import DockerHostDriver, DockerHostPingResult
from fourdrinier.hosts.drivers import HostDriverRegistry
from fourdrinier.hosts.kubernetes import (
    KubernetesHostDriver,
    KubernetesHostPingResult,
)
from fourdrinier.hosts.service import HostService

router: APIRouter = APIRouter(prefix="/hosts", tags=["hosts"])


def _host_service(session: DbSession, settings: SettingsDep) -> HostService:
    try:
        cipher: FernetSecretCipher = FernetSecretCipher.from_settings(settings)
    except EncryptionKeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    drivers: HostDriverRegistry = HostDriverRegistry(
        DockerHostDriver(cipher),
        KubernetesHostDriver(cipher),
    )
    service: HostService = HostService(
        session=session,
        drivers=drivers,
        secret_encryptor=cipher,
    )
    return service


def _docker_host_read(host: Host) -> DockerHostRead:
    details: DockerHostDetails | None = host.docker_details
    if details is None:
        raise RuntimeError(f"Docker host {host.id} has no Docker details")
    response: DockerHostRead = DockerHostRead(
        id=host.id,
        name=host.name,
        enabled=host.enabled,
        labels=host.labels,
        last_seen_at=host.last_seen_at,
        created_at=host.created_at,
        updated_at=host.updated_at,
        address=details.address,
        port=details.port,
        username=details.username,
        keypair_id=details.keypair_id,
        host_key_fingerprint=details.host_key_fingerprint,
    )
    return response


def _kubernetes_host_read(host: Host) -> KubernetesHostRead:
    details: KubernetesHostDetails | None = host.kubernetes_details
    if details is None:
        raise RuntimeError(f"Kubernetes host {host.id} has no Kubernetes details")
    response: KubernetesHostRead = KubernetesHostRead(
        id=host.id,
        name=host.name,
        enabled=host.enabled,
        labels=host.labels,
        last_seen_at=host.last_seen_at,
        created_at=host.created_at,
        updated_at=host.updated_at,
        api_url=details.api_url,
        namespace=details.namespace,
    )
    return response


def _host_read(host: Host) -> DockerHostRead | KubernetesHostRead:
    if host.type is HostType.DOCKER:
        return _docker_host_read(host)
    return _kubernetes_host_read(host)


def _name_conflict(name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"host with name {name!r} already exists",
    )


def _not_found(exc: HostNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
    )


@router.post("", response_model=HostRead, status_code=status.HTTP_201_CREATED)
async def create_host(
    body: HostCreate, session: DbSession, settings: SettingsDep
) -> DockerHostRead | KubernetesHostRead:
    if isinstance(body, DockerHostCreate):
        if await keypairs_crud.get_keypair(session, body.keypair_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"keypair {body.keypair_id} not found",
            )
    service: HostService = _host_service(session, settings)
    try:
        host: Host = await service.create(body)
    except HostNameConflictError as exc:
        raise _name_conflict(body.name) from exc
    return _host_read(host)


@router.get("", response_model=HostListResponse)
async def list_hosts(
    session: DbSession,
    settings: SettingsDep,
    type: Literal["docker", "kubernetes"] | None = None,
) -> list[DockerHostRead | KubernetesHostRead]:
    service: HostService = _host_service(session, settings)
    host_type: HostType | None = HostType(type) if type is not None else None
    hosts: list[Host] = await service.list(host_type)
    return [_host_read(host) for host in hosts]


@router.get("/{host_id}", response_model=HostRead)
async def get_host(
    host_id: uuid.UUID, session: DbSession, settings: SettingsDep
) -> DockerHostRead | KubernetesHostRead:
    service: HostService = _host_service(session, settings)
    try:
        host: Host = await service.get(host_id)
    except HostNotFoundError as exc:
        raise _not_found(exc) from exc
    return _host_read(host)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: uuid.UUID, session: DbSession, settings: SettingsDep) -> None:
    service: HostService = _host_service(session, settings)
    try:
        await service.delete(host_id)
    except HostNotFoundError as exc:
        raise _not_found(exc) from exc


def _docker_ping_response(result: DockerHostPingResult) -> DockerPingResponse:
    response: DockerPingResponse = DockerPingResponse(
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
    return response


def _kubernetes_ping_response(result: KubernetesHostPingResult) -> KubernetesPingResponse:
    response: KubernetesPingResponse = KubernetesPingResponse(
        latency_ms=result.latency_ms,
        git_version=result.git_version,
        platform=result.platform,
        username=result.username,
        namespace=result.namespace,
    )
    return response


@router.post("/{host_id}/ping", response_model=HostPingResponse)
async def ping_host(
    host_id: uuid.UUID, session: DbSession, settings: SettingsDep
) -> DockerPingResponse | KubernetesPingResponse:
    service: HostService = _host_service(session, settings)
    try:
        result: HostPingResult = await service.ping(host_id)
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
    if isinstance(result, DockerHostPingResult):
        return _docker_ping_response(result)
    if isinstance(result, KubernetesHostPingResult):
        return _kubernetes_ping_response(result)
    raise RuntimeError(f"host {host_id} returned an unsupported ping result")


__all__: list[str] = ["router"]
