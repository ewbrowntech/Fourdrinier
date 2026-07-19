"""
servers.py

Expose CRUD endpoints for provider-independent logical servers.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from fourdrinier.api.deps import ServerServiceDep
from fourdrinier.db.models import Server
from fourdrinier.schemas import ServerCreate, ServerRead, ServerUpdate
from fourdrinier.servers import (
    ServerNameConflictError,
    ServerNotFoundError,
    ServerResourceMinimumError,
    ServerVersionUnsupportedError,
)

router: APIRouter = APIRouter(prefix="/servers", tags=["servers"])


def _not_found(exc: ServerNotFoundError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _name_conflict(exc: ServerNameConflictError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _unprocessable(
    exc: ServerResourceMinimumError | ServerVersionUnsupportedError,
) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


@router.post("", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(body: ServerCreate, service: ServerServiceDep) -> Server:
    """Save a logical server without provisioning it.

    Args:
        body: Validated server configuration.
        service: Request-scoped logical server service.

    Returns:
        The newly saved server configuration.

    Raises:
        HTTPException: If the name is in use, resources are below the runtime minimum,
            or the runtime does not support the requested Minecraft version.
    """
    try:
        server: Server = await service.create(body)
    except ServerNameConflictError as exc:
        raise _name_conflict(exc) from exc
    except (ServerResourceMinimumError, ServerVersionUnsupportedError) as exc:
        raise _unprocessable(exc) from exc
    return server


@router.get("", response_model=list[ServerRead])
async def list_servers(service: ServerServiceDep) -> list[Server]:
    """List all saved logical servers.

    Args:
        service: Request-scoped logical server service.

    Returns:
        Saved server configurations in name order.
    """
    servers: list[Server] = await service.list()
    return servers


@router.get("/{server_id}", response_model=ServerRead)
async def get_server(server_id: uuid.UUID, service: ServerServiceDep) -> Server:
    """Get one saved logical server.

    Args:
        server_id: Identifier of the requested server.
        service: Request-scoped logical server service.

    Returns:
        The matching saved server configuration.

    Raises:
        HTTPException: If the server does not exist.
    """
    try:
        server: Server = await service.get(server_id)
    except ServerNotFoundError as exc:
        raise _not_found(exc) from exc
    return server


@router.patch("/{server_id}", response_model=ServerRead)
async def update_server(
    server_id: uuid.UUID,
    body: ServerUpdate,
    service: ServerServiceDep,
) -> Server:
    """Update editable metadata, version, and resources for a saved logical server.

    Args:
        server_id: Identifier of the server to update.
        body: Validated partial update.
        service: Request-scoped logical server service.

    Returns:
        The updated saved server configuration.

    Raises:
        HTTPException: If the server is missing, the name is in use, or the resources
            or Minecraft version are invalid for the runtime.
    """
    try:
        server: Server = await service.update(server_id, body)
    except ServerNotFoundError as exc:
        raise _not_found(exc) from exc
    except ServerNameConflictError as exc:
        raise _name_conflict(exc) from exc
    except (ServerResourceMinimumError, ServerVersionUnsupportedError) as exc:
        raise _unprocessable(exc) from exc
    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(server_id: uuid.UUID, service: ServerServiceDep) -> None:
    """Delete a saved logical server.

    Args:
        server_id: Identifier of the server to delete.
        service: Request-scoped logical server service.

    Raises:
        HTTPException: If the server does not exist.
    """
    try:
        await service.delete(server_id)
    except ServerNotFoundError as exc:
        raise _not_found(exc) from exc


__all__: list[str] = ["router"]
