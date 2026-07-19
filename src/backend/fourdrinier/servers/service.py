"""
service.py

Coordinate logical server persistence and runtime deployment translation.
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.crud import servers as servers_crud
from fourdrinier.db.models import Server
from fourdrinier.schemas.server import ServerCreate, ServerUpdate
from fourdrinier.servers.deployment import DeploymentSpec
from fourdrinier.servers.errors import (
    ServerNameConflictError,
    ServerNotFoundError,
    ServerResourceMinimumError,
)
from fourdrinier.servers.runtimes import RuntimeAdapter, RuntimeRegistry
from fourdrinier.servers.types import (
    ServerDesiredState,
    ServerId,
    ServerRuntime,
)


def _is_server_name_conflict(exc: IntegrityError) -> bool:
    original: BaseException = exc.orig
    message: str = str(original).lower()
    return "uq_servers_name" in message or "unique constraint failed: servers.name" in message


def _validate_resource_minimums(
    runtime: RuntimeAdapter,
    cpu_millicores: int,
    memory_bytes: int,
) -> None:
    minimum_cpu: int = runtime.minimum_resources.cpu_millicores
    if cpu_millicores < minimum_cpu:
        raise ServerResourceMinimumError(
            f"{runtime.runtime.value} requires at least {minimum_cpu} CPU millicores"
        )
    minimum_memory: int = runtime.minimum_resources.memory_bytes
    if memory_bytes < minimum_memory:
        raise ServerResourceMinimumError(
            f"{runtime.runtime.value} requires at least {minimum_memory} memory bytes"
        )


class ServerService:
    """Implement logical server use cases across persistence and runtime boundaries."""

    def __init__(self, session: AsyncSession, runtimes: RuntimeRegistry) -> None:
        """Initialize the service with persistence and runtime dependencies.

        Args:
            session: Session that owns transactions for server write operations.
            runtimes: Registry used to select runtime deployment adapters.
        """
        self._session: AsyncSession = session
        self._runtimes: RuntimeRegistry = runtimes

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
            ServerResourceMinimumError: If an allocation is below its runtime minimum.
        """
        runtime_type: ServerRuntime = ServerRuntime(request.runtime)
        runtime: RuntimeAdapter = self._runtimes.for_runtime(runtime_type)
        _validate_resource_minimums(
            runtime,
            request.cpu_millicores,
            request.memory_bytes,
        )
        server: Server = Server(
            name=request.name,
            runtime=runtime_type,
            minecraft_version=runtime.minecraft_version,
            cpu_millicores=request.cpu_millicores,
            memory_bytes=request.memory_bytes,
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

    async def deployment_spec(self, server_id: ServerId) -> DeploymentSpec:
        """Translate a saved logical server into a deployment specification.

        Args:
            server_id: Identifier of the logical server to translate.

        Returns:
            A provider-neutral deployment specification from its runtime adapter.

        Raises:
            ServerNotFoundError: If the requested server does not exist.
        """
        server: Server = await self._get_required(server_id)
        runtime: RuntimeAdapter = self._runtimes.for_runtime(server.runtime)
        specification: DeploymentSpec = runtime.deployment_spec(server)
        return specification

    async def update(self, server_id: ServerId, request: ServerUpdate) -> Server:
        """Update editable metadata and resource allocation for a logical server.

        Args:
            server_id: Identifier of the server to modify.
            request: Validated partial update.

        Returns:
            The updated logical server.

        Raises:
            ServerNotFoundError: If the requested server does not exist.
            ServerNameConflictError: If the requested server name already exists.
            ServerResourceMinimumError: If an allocation is below its runtime minimum.
        """
        try:
            server: Server = await self._get_required(server_id)
            resources_supplied: bool = bool(
                {"cpu_millicores", "memory_bytes"} & request.model_fields_set
            )
            resources_changed: bool = False
            cpu_millicores: int = server.cpu_millicores
            if "cpu_millicores" in request.model_fields_set:
                cpu_millicores = cast(int, request.cpu_millicores)
                resources_changed = resources_changed or server.cpu_millicores != cpu_millicores
            memory_bytes: int = server.memory_bytes
            if "memory_bytes" in request.model_fields_set:
                memory_bytes = cast(int, request.memory_bytes)
                resources_changed = resources_changed or server.memory_bytes != memory_bytes
            if resources_supplied:
                runtime: RuntimeAdapter = self._runtimes.for_runtime(server.runtime)
                _validate_resource_minimums(runtime, cpu_millicores, memory_bytes)
            if "name" in request.model_fields_set:
                server.name = cast(str, request.name)
            if resources_changed:
                server.cpu_millicores = cpu_millicores
                server.memory_bytes = memory_bytes
                server.spec_generation += 1
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
