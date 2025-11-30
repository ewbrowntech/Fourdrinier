"""
conftest.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Set up fixtures for testing

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import os


os.environ["DB_URL"] = "sqlite+aiosqlite:///./test.db"

from typing import AsyncGenerator

import pytest
from httpx import ASGITransport
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine

from fourdrinier.core.config import DB_URL
from fourdrinier.db.models import Base
from fourdrinier.db.session import get_db
from fourdrinier.main import app


@pytest.fixture()
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine: AsyncEngine = create_async_engine(DB_URL)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionMaker = async_sessionmaker(bind=test_db_engine)
    async with AsyncSessionMaker() as session:
        yield session

    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
