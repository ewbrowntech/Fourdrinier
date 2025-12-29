"""
servers.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Endpoints for interacting with server objects.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db import crud
from fourdrinier.db.models import Server
from fourdrinier.db.schema import ServerCreate
from fourdrinier.db.schema import ServerResponse
from fourdrinier.db.schema import ServerUpdate
from fourdrinier.db.session import get_db
from fourdrinier.dependencies.deploy.start_container import delete_server_resources
from fourdrinier.dependencies.deploy.start_container import get_server_status
from fourdrinier.dependencies.deploy.start_container import start_container
from fourdrinier.dependencies.deploy.start_container import stop_container


router = APIRouter()


@router.post("/", status_code=201, response_model=ServerResponse)
async def create_server(server_input: ServerCreate, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Create a new server
    """
    server: Server = await crud.create_server(db, server_input)
    return {
        "id": server.id,
        "name": server.name,
        "loader": server.loader,
        "game_version": server.game_version,
        "status": "created",  # New servers start in created state
    }


@router.get("/", status_code=200, response_model=list[ServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """
    List all servers with their current status
    """
    servers: list[Server] = await crud.list_servers(db)

    # Enrich each server with its Kubernetes status
    servers_with_status = []
    for server in servers:
        status = await get_server_status(server.id)
        server_dict = {
            "id": server.id,
            "name": server.name,
            "loader": server.loader,
            "game_version": server.game_version,
            "status": status,
        }
        servers_with_status.append(server_dict)

    return servers_with_status


@router.get("/{server_id}", status_code=200, response_model=ServerResponse)
async def get_server(server_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Get a server by ID with its current status
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Enrich with Kubernetes status
    status = await get_server_status(server.id)
    return {
        "id": server.id,
        "name": server.name,
        "loader": server.loader,
        "game_version": server.game_version,
        "status": status,
    }


@router.put("/{server_id}", status_code=200, response_model=ServerResponse)
async def update_server(
    server_id: str, server_update: ServerUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update a server's details
    """
    try:
        server: Server = await crud.update_server(db, server_id, server_update)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Enrich with Kubernetes status
    status = await get_server_status(server.id)
    return {
        "id": server.id,
        "name": server.name,
        "loader": server.loader,
        "game_version": server.game_version,
        "status": status,
    }


@router.delete("/{server_id}", status_code=200)
async def delete_server(server_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a server and all its Kubernetes resources
    """
    # Delete Kubernetes resources (Pod, PVC, Service)
    await delete_server_resources(server_id)

    # Remove the server from the database
    try:
        await crud.delete_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    return


@router.post("/{server_id}/start", status_code=201)
async def start_server(server_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Start a Minecraft server in Kubernetes
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Start the server in Kubernetes
    pod_name: str = await start_container(
        server_name=server.name, server_id=server.id, game_version=server.game_version
    )

    return JSONResponse(content={"pod": {"name": pod_name, "namespace": "minecraft"}})


@router.put("/{server_id}/stop", status_code=200)
async def stop_server(server_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Stop a Minecraft server
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    await stop_container(server.id)

    return JSONResponse(content={"message": "Server stopped"})
