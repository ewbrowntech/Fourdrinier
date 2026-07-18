"""
service.py

Coordinate logical server persistence without provisioning remote resources.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.crud import servers as servers_crud
from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerCreate, ServerUpdate
from fourdrinier.servers.errors import ServerNameConflictError, ServerNotFoundError
from fourdrinier.servers.types import (
    PUMPKIN_MINECRAFT_VERSION,
    ServerDesiredState,
    ServerId,
    ServerRuntime,
)


def _is_server_name_conflict(exc: IntegrityError) -> bool:
    original: BaseException = exc.orig
    message: str = str(original).lower()
    return "uq_servers_name" in message or "unique constraint failed: servers.name" in message


class ServerService:
    """Implement logical server use cases within the local database boundary."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize the service with its request-scoped transaction.

        Args:
            session: Session that owns transactions for server write operations.
        """
        self._session: AsyncSession = session

    async def _get_required(self, server_id: ServerId) -> Server:
        server: Server | None = await servers_crud.get_server(self._session, server_id)
        if server is None:
            raise ServerNotFoundError(f"server {server_id} not found")
        return server

    async def create(self, request: ServerCreate) -> Server:
        """Save a stopped, unassigned Pumpkin server configuration.

        Args:
            request: Validated logical server creation request.

        Returns:
            The newly persisted logical server.

        Raises:
            ServerNameConflictError: If the requested server name already exists.
        """
        server: Server = Server(
            name=request.name,
            runtime=ServerRuntime.PUMPKIN,
            minecraft_version=PUMPKIN_MINECRAFT_VERSION,
            desired_state=ServerDesiredState.STOPPED,
            spec_generation=1,
        )
        try:
            created: Server = await servers_crud.create_server(self._session, server)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_server_name_conflict(exc):
                raise ServerNameConflictError(
                    f"server with name {request.name!r} already exists"
                ) from exc
            raise
        except Exception:
            await self._session.rollback()
            raise
        return created

    async def list(self) -> list[Server]:
        """List all saved logical servers.

        Returns:
            Logical servers ordered by name.
        """
        servers: list[Server] = await servers_crud.list_servers(self._session)
        return servers

    async def get(self, server_id: ServerId) -> Server:
        """Get a logical server by identifier.

        Args:
            server_id: Identifier of the requested server.

        Returns:
            The matching logical server.

        Raises:
            ServerNotFoundError: If the requested server does not exist.
        """
        server: Server = await self._get_required(server_id)
        return server

    async def update(self, server_id: ServerId, request: ServerUpdate) -> Server:
        """Update the editable metadata of a logical server.

        Args:
            server_id: Identifier of the server to modify.
            request: Validated partial update.

        Returns:
            The updated logical server.

        Raises:
            ServerNotFoundError: If the requested server does not exist.
            ServerNameConflictError: If the requested server name already exists.
        """
        try:
            server: Server = await self._get_required(server_id)
            if "name" in request.model_fields_set:
                server.name = cast(str, request.name)
            updated: Server = await servers_crud.update_server(self._session, server)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if _is_server_name_conflict(exc):
                raise ServerNameConflictError(
                    f"server with name {request.name!r} already exists"
                ) from exc
            raise
        except Exception:
            await self._session.rollback()
            raise
        return updated

    async def delete(self, server_id: ServerId) -> None:
        """Delete an unprovisioned logical server.

        Args:
            server_id: Identifier of the server to delete.

        Raises:
            ServerNotFoundError: If the requested server does not exist.
        """
        try:
            server: Server = await self._get_required(server_id)
            await servers_crud.delete_server(self._session, server)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise


__all__: list[str] = ["ServerService"]
