"""
test_list_servers.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Test GET /servers/

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from unittest.mock import MagicMock

from httpx import AsyncClient
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def test_list_servers_000_nominal_no_servers(
    client: AsyncClient, test_db: AsyncSession
) -> None:
    """
    Test 000 - Nominal
    Conditions: One valid server object
    Result: HTTP 201 - Server object returned
    """
    # Make a request to the server creation endpoint
    response: Response = await client.get("servers/")

    # Ensure the correct response is returned
    assert response.status_code == 200
    assert response.json() == []


async def test_list_servers_001_nominal_two_servers(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 000 - Nominal
    Conditions: One valid server object
    Result: HTTP 201 - Server object returned
    """
    # Add two servers to the database
    server_1: Server = Server(id="1", name="Test Server 1", loader="paper", game_version="1.20.0")
    server_2: Server = Server(id="2", name="Test Server 2", loader="fabric", game_version="1.20.0")
    test_db.add(server_1)
    test_db.add(server_2)
    await test_db.commit()

    # Make a request to the server creation endpoint
    response: Response = await client.get("servers/")

    # Ensure the correct response is returned
    assert response.status_code == 200
    assert len(response.json()) == 2

    await test_db.refresh(server_1)
    await test_db.refresh(server_2)
    assert response.json() == [
        {
            "id": server_1.id,
            "name": server_1.name,
            "loader": server_1.loader,
            "game_version": server_1.game_version,
            "modrinth_projects": server_1.modrinth_projects,
            "status": "created",
        },
        {
            "id": server_2.id,
            "name": server_2.name,
            "loader": server_2.loader,
            "game_version": server_2.game_version,
            "modrinth_projects": server_2.modrinth_projects,
            "status": "created",
        },
    ]
