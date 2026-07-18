"""
test_server_constraints.py

Integration tests for logical server database constraints.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.models import Server
from fourdrinier.servers import PUMPKIN_MINECRAFT_VERSION


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"runtime": "paper"}, id="runtime"),
        pytest.param({"desired_state": "paused"}, id="desired-state"),
        pytest.param({"spec_generation": 0}, id="spec-generation"),
    ],
)
async def test_server_constraints_001_anomalous_invalid_persisted_value_is_rejected(
    app: FastAPI,
    overrides: dict[str, object],
) -> None:
    """Test 001 - Anomalous
    Condition: A direct insert violates a runtime, desired-state, or generation invariant
    Result: IntegrityError is raised and no logical server row is persisted
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    server_id: uuid.UUID = uuid.uuid4()
    values: dict[str, object] = {
        "id": server_id.hex,
        "name": "invalid-server",
        "runtime": "pumpkin",
        "minecraft_version": PUMPKIN_MINECRAFT_VERSION,
        "desired_state": "stopped",
        "spec_generation": 1,
        **overrides,
    }
    statement: str = """
        INSERT INTO servers (
            id, name, runtime, minecraft_version, desired_state, spec_generation
        ) VALUES (
            :id, :name, :runtime, :minecraft_version, :desired_state, :spec_generation
        )
    """

    # Act
    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(text(statement), values)
            await session.commit()
        await session.rollback()

    # Assert
    async with session_factory() as session:
        persisted: Server | None = await session.get(Server, server_id)
    assert persisted is None
