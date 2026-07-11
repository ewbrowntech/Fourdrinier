"""API v1 routers."""

from fastapi import APIRouter

from fourdrinier.api.v1 import hosts

router: APIRouter = APIRouter(prefix="/api/v1")
router.include_router(hosts.router)

__all__ = ["router"]
