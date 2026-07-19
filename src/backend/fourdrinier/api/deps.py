"""
deps.py

Compose application services used by the HTTP API.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status

from fourdrinier.core.crypto import EncryptionKeyError, FernetSecretCipher
from fourdrinier.core.deps import SettingsDep
from fourdrinier.db.deps import DbSession
from fourdrinier.hosts.docker import DockerHostDriver
from fourdrinier.hosts.drivers import HostDriverRegistry
from fourdrinier.hosts.kubernetes import KubernetesHostDriver
from fourdrinier.hosts.service import HostService
from fourdrinier.servers.pumpkin import PumpkinRuntime
from fourdrinier.servers.runtimes import RuntimeRegistry
from fourdrinier.servers.service import ServerService


def get_host_service(session: DbSession, settings: SettingsDep) -> HostService:
    """Build a host service for the current request.

    Args:
        session: Request-scoped database session.
        settings: Application settings containing the secret-encryption key.

    Returns:
        A host service configured with every registered provider driver.

    Raises:
        HTTPException: If host credentials cannot be encrypted or decrypted.
    """
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


HostServiceDep = Annotated[HostService, Depends(get_host_service)]


def get_server_service(session: DbSession) -> ServerService:
    """Build a logical server service for the current request.

    Args:
        session: Request-scoped database session.

    Returns:
        A logical server service configured with every runtime adapter.
    """
    runtimes: RuntimeRegistry = RuntimeRegistry(PumpkinRuntime())
    service: ServerService = ServerService(session=session, runtimes=runtimes)
    return service


ServerServiceDep = Annotated[ServerService, Depends(get_server_service)]

__all__: list[str] = [
    "HostServiceDep",
    "ServerServiceDep",
    "get_host_service",
    "get_server_service",
]
