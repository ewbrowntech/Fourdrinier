"""
test_get_server.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Test GET /servers/{server_id}

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from httpx import AsyncClient
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def test_get_server_000_nominal(client: AsyncClient, test_db: AsyncSession) -> None:
    """
    Test 000 - Nominal
    Conditions: Server1 in database, request Server1
    Result: HTTP 200 - `server1`
    """
    # Add a server to the database
    server1 = Server(id="1", name="Test Server", loader="paper", game_version="1.20.0")
    test_db.add(server1)
    await test_db.commit()

    # Make a request to the server creation endpoint
    response: Response = await client.get("servers/1")

    # Ensure the correct response is returned
    assert response.status_code == 200
    await test_db.refresh(server1)
    assert response.json() == {
        "id": server1.id,
        "name": server1.name,
        "loader": server1.loader,
        "game_version": server1.game_version,
    }


async def test_get_server_001_anomalous_nonexistent_server(
    client: AsyncClient, test_db: AsyncSession
) -> None:
    """
    Test 001 - Anomalous
    Conditions: Server1 in database, request Server2
    Result: HTTP 404 - "Server not found"
    """
    # Add a server to the database
    server1 = Server(id="1", name="Test Server", loader="paper", game_version="1.20.0")
    test_db.add(server1)
    await test_db.commit()

    # Make a request to the server creation endpoint
    response: Response = await client.get("servers/2")

    # Ensure the correct response is returned
    assert response.status_code == 404
    assert response.json() == {"detail": "Server not found"}
