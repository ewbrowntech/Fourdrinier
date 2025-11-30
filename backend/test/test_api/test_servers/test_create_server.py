"""
test_create_server.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Test POST /servers/

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from typing import Sequence
from typing import Tuple

from httpx import AsyncClient
from httpx import Response
from sqlalchemy import Result
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def test_create_server_000_nominal(client: AsyncClient, test_db: AsyncSession) -> None:
    """
    Test 000 - Nominal
    Conditions: One valid server object
    Result: HTTP 201 - Server object returned
    """
    # Make a request to the server creation endpoint
    response: Response = await client.post(
        "servers/", json={"name": "Test Server", "loader": "paper", "game_version": "1.20.0"}
    )

    # Ensure the correct response is returned
    assert response.status_code == 201
    assert response.json()["name"] == "Test Server"
    assert response.json()["loader"] == "paper"
    assert response.json()["game_version"] == "1.20.0"

    # Ensure the server was added to the database
    result: Result[Tuple[Server]] = await test_db.execute(select(Server))
    servers: Sequence[Server] = result.scalars().all()
    assert len(servers) == 1
    server: Server = servers[0]
    assert server.name == "Test Server"
    assert server.loader == "paper"
    assert server.game_version == "1.20.0"
