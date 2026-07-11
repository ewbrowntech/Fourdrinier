"""Shared test fixtures: app with a temp SQLite DB and a test Fernet key."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI

from fourdrinier.app import create_app
from fourdrinier.core.settings import Settings
from fourdrinier.db.base import Base
from fourdrinier.db.session import create_engine, create_session_factory


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        env="test",
        database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db",
        encryption_key=Fernet.generate_key().decode(),
    )


@pytest.fixture
async def app(settings: Settings) -> AsyncIterator[FastAPI]:
    """App with state wired directly (httpx's ASGITransport skips lifespan)."""
    application = create_app(settings)
    engine = create_engine(settings)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    application.state.settings = settings
    application.state.engine = engine
    application.state.session_factory = create_session_factory(engine)
    yield application
    await engine.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
