"""Async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from fourdrinier.core.settings import Settings


def ensure_sqlite_parent(database_url: str) -> None:
    """Create the parent directory for a file-backed SQLite URL if needed."""
    if not database_url.startswith("sqlite"):
        return
    # sqlite+aiosqlite:///relative/path or sqlite+aiosqlite:////absolute/path
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        return
    raw_path = database_url.removeprefix(prefix)
    if raw_path in {"", ":memory:"} or raw_path.startswith(":memory:"):
        return
    path = Path(raw_path)
    if not path.is_absolute():
        # Relative to process CWD; still ensure parent exists.
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


def create_engine(settings: Settings) -> AsyncEngine:
    """Build an async SQLAlchemy engine from settings."""
    ensure_sqlite_parent(settings.database_url)
    return create_async_engine(
        settings.database_url,
        echo=settings.env == "debug",
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an ``async_sessionmaker`` bound to ``engine``."""
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped async session (for FastAPI ``Depends``)."""
    async with session_factory() as session:
        yield session


__all__ = ["create_engine", "create_session_factory", "ensure_sqlite_parent", "get_session"]
