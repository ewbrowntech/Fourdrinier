from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from fourdrinier.api.v1 import router as api_v1_router
from fourdrinier.core.deps import get_settings
from fourdrinier.core.settings import SETTINGS, Settings
from fourdrinier.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Attaches settings to ``app.state.settings`` during lifespan startup so
    route handlers can access config via ``get_settings``. Also wires the
    async SQLAlchemy engine and session factory onto ``app.state``.

    Args:
        settings: Application configuration. Defaults to ``SETTINGS`` loaded
            from the environment. Pass an explicit instance in tests or other
            programmatic use.

    Returns:
        A configured FastAPI application instance.
    """
    config: Settings = settings or SETTINGS

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = config
        engine = create_engine(config)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        yield
        await engine.dispose()

    app: FastAPI = FastAPI(
        title="Fourdrinier",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=config.docs_url,
        redoc_url=config.redoc_url,
        openapi_url=config.openapi_url,
    )

    app.include_router(api_v1_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(_settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {"status": "ready"}

    return app


app: FastAPI = create_app()
