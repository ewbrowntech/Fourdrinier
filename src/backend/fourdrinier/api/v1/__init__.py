"""API v1 routers."""

from fastapi import APIRouter

from fourdrinier.api.v1 import hosts, keypairs, runtimes, servers

router: APIRouter = APIRouter(prefix="/api/v1")
router.include_router(keypairs.router)
router.include_router(hosts.router)
router.include_router(runtimes.router)
router.include_router(servers.router)

__all__ = ["router"]
