"""
session.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Set up the database session for use by the FastAPI application.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.orm import DeclarativeBase

from fourdrinier.core import config


# Create a base class for retrieval of model metadata
class Base(DeclarativeBase):
    pass


# Create an asynchronous database engine
async_engine: AsyncEngine = create_async_engine(config.DB_URL)
AsyncSessionMaker = async_sessionmaker(bind=async_engine)


# Return an asynchronous database session via dependency injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionMaker() as session:
        try:
            yield session
        except Exception:
            raise
