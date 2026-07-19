"""
runtimes.py

Expose discovery endpoints for registered Minecraft runtimes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from fourdrinier.api.deps import RuntimeRegistryDep
from fourdrinier.servers.errors import RuntimeNotRegisteredError
from fourdrinier.servers.runtimes import RuntimeAdapter
from fourdrinier.servers.types import ServerRuntime

router: APIRouter = APIRouter(prefix="/runtimes", tags=["runtimes"])


def _not_registered(exc: RuntimeNotRegisteredError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/{runtime}/versions", response_model=list[str])
async def list_runtime_versions(
    runtime: ServerRuntime,
    runtimes: RuntimeRegistryDep,
) -> list[str]:
    """List Minecraft versions a registered runtime can deploy.

    Args:
        runtime: Logical server runtime whose versions are requested.
        runtimes: Registry of adapters for every supported runtime.

    Returns:
        Minecraft versions accepted by the runtime.

    Raises:
        HTTPException: If no adapter is registered for the requested runtime.
    """
    try:
        adapter: RuntimeAdapter = runtimes.for_runtime(runtime)
    except RuntimeNotRegisteredError as exc:
        raise _not_registered(exc) from exc
    versions: list[str] = await adapter.list_versions()
    return versions


__all__: list[str] = ["router"]
