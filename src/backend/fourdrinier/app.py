from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from fourdrinier.core.deps import get_settings
from fourdrinier.core.settings import SETTINGS, Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Attaches settings to ``app.state.settings`` during lifespan startup so
    route handlers can access config via ``get_settings``.

    Args:
        settings: Application configuration. Defaults to ``SETTINGS`` loaded
            from the environment. Pass an explicit instance in tests or other
            programmatic use.

    Returns:
        A configured FastAPI application instance.
    """
    config = settings or SETTINGS

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = config
        yield

    app = FastAPI(
        title="Fourdrinier",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=config.docs_url,
        redoc_url=config.redoc_url,
        openapi_url=config.openapi_url,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    async def ready(_settings: Settings = Depends(get_settings)) -> dict[str, str]:
        return {"status": "ready"}

    return app


app = create_app()
