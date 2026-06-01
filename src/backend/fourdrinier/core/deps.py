from fastapi import Request

from fourdrinier.core.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


__all__ = ["get_settings"]
