"""API v1 routers."""

from fastapi import APIRouter

from fourdrinier.api.v1 import hosts, keypairs

router: APIRouter = APIRouter(prefix="/api/v1")
router.include_router(keypairs.router)
router.include_router(hosts.router)

__all__ = ["router"]
