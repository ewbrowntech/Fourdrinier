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

__all__: list[str] = ["HostServiceDep", "get_host_service"]
