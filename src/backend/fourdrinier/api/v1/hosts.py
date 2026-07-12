"""Host API — register Docker and Kubernetes hosts and validate connectivity."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from fourdrinier.core.crypto import (
    DecryptionError,
    EncryptionKeyError,
    encrypt_secret,
)
from fourdrinier.core.deps import SettingsDep
from fourdrinier.db.crud import hosts as hosts_crud
from fourdrinier.db.crud import kubernetes_hosts as k8s_hosts_crud
from fourdrinier.db.crud import ssh_keypairs as keypairs_crud
from fourdrinier.db.deps import DbSession
from fourdrinier.db.models import DockerHost, KubernetesHost
from fourdrinier.db.schemas import (
    DockerPingResponse,
    HostCreate,
    HostRead,
    KubernetesHostCreate,
    KubernetesPingResponse,
    PingHostKey,
    PingResponse,
)
from fourdrinier.hosts.docker import service as docker_service
from fourdrinier.hosts.docker.errors import (
    HostKeyMismatchError,
    HostUnreachableError,
    SSHAuthError,
)
from fourdrinier.hosts.kubernetes import service as k8s_service
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)

router: APIRouter = APIRouter(prefix="/hosts", tags=["hosts"])

AnyHost = DockerHost | KubernetesHost


async def _get_any_host_or_404(session: DbSession, host_id: uuid.UUID) -> AnyHost:
    # Lookup order (docker first) is arbitrary; UUIDs never collide in practice.
    host: AnyHost | None = await hosts_crud.get_host(session, host_id)
    if host is None:
        host = await k8s_hosts_crud.get_host(session, host_id)
    if host is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"host {host_id} not found",
        )
    return host


def _name_conflict(name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=f"host with name {name!r} already exists",
    )


@router.post("", response_model=HostRead, status_code=status.HTTP_201_CREATED)
async def create_host(
    body: HostCreate, session: DbSession, settings: SettingsDep
) -> AnyHost:
    if isinstance(body, KubernetesHostCreate):
        # Names must be unique across host types so the merged list is unambiguous.
        if await hosts_crud.get_host_by_name(session, body.name) is not None:
            raise _name_conflict(body.name)
        try:
            token_encrypted: bytes = encrypt_secret(body.token.encode(), settings)
        except EncryptionKeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        try:
            return await k8s_hosts_crud.create_host(
                session,
                name=body.name,
                api_url=body.api_url,
                ca_cert_pem=body.ca_cert_pem,
                token_encrypted=token_encrypted,
                namespace=body.namespace,
                enabled=body.enabled,
                labels=body.labels,
            )
        except IntegrityError as exc:
            raise _name_conflict(body.name) from exc

    if await keypairs_crud.get_keypair(session, body.keypair_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"keypair {body.keypair_id} not found",
        )
    if await k8s_hosts_crud.get_host_by_name(session, body.name) is not None:
        raise _name_conflict(body.name)
    try:
        return await hosts_crud.create_host(
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
        raise _name_conflict(body.name) from exc


@router.get("", response_model=list[HostRead])
async def list_hosts(
    session: DbSession,
    type: Literal["docker", "kubernetes"] | None = None,
) -> list[AnyHost]:
    docker_hosts: list[DockerHost] = (
        await hosts_crud.list_hosts(session) if type in (None, "docker") else []
    )
    k8s_hosts: list[KubernetesHost] = (
        await k8s_hosts_crud.list_hosts(session)
        if type in (None, "kubernetes")
        else []
    )
    return sorted([*docker_hosts, *k8s_hosts], key=lambda host: host.name)


@router.get("/{host_id}", response_model=HostRead)
async def get_host(host_id: uuid.UUID, session: DbSession) -> AnyHost:
    return await _get_any_host_or_404(session, host_id)


@router.delete("/{host_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_host(host_id: uuid.UUID, session: DbSession) -> None:
    host: AnyHost = await _get_any_host_or_404(session, host_id)
    if isinstance(host, KubernetesHost):
        await k8s_hosts_crud.delete_host(session, host)
    else:
        await hosts_crud.delete_host(session, host)


async def _ping_docker_host(
    session: DbSession, host: DockerHost, settings: SettingsDep
) -> DockerPingResponse:
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
    return DockerPingResponse(
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


async def _ping_kubernetes_host(
    session: DbSession, host: KubernetesHost, settings: SettingsDep
) -> KubernetesPingResponse:
    try:
        result: k8s_service.PingResult = await k8s_service.ping_host(
            session, host, settings
        )
    except TLSVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except KubernetesAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ClusterUnreachableError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except KubernetesRBACError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (EncryptionKeyError, DecryptionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return KubernetesPingResponse(
        latency_ms=result.latency_ms,
        git_version=result.git_version,
        platform=result.platform,
        username=result.username,
        namespace=result.namespace,
    )


@router.post("/{host_id}/ping", response_model=PingResponse)
async def ping_host(
    host_id: uuid.UUID, session: DbSession, settings: SettingsDep
) -> DockerPingResponse | KubernetesPingResponse:
    host: AnyHost = await _get_any_host_or_404(session, host_id)
    if isinstance(host, KubernetesHost):
        return await _ping_kubernetes_host(session, host, settings)
    return await _ping_docker_host(session, host, settings)


__all__ = ["router"]
