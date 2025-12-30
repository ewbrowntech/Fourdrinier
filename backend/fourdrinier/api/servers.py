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
from fastapi.responses import StreamingResponse
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
from fourdrinier.dependencies.deploy.start_container import stream_server_logs
from fourdrinier.services.modrinth_client import get_collection_projects


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
        "modrinth_projects": server.modrinth_projects,
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
            "modrinth_projects": server.modrinth_projects,
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
        "modrinth_projects": server.modrinth_projects,
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
        "modrinth_projects": server.modrinth_projects,
        "status": status,
    }


@router.post("/{server_id}/import-collection", status_code=200)
async def import_modrinth_collection(
    server_id: str, collection_url: str, db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """
    Import Modrinth projects from a collection URL and append to server's project list
    """
    # Get the server
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Fetch projects from Modrinth collection
    try:
        new_projects = await get_collection_projects(collection_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch collection from Modrinth: {str(e)}")

    # Merge with existing projects (deduplicate)
    existing_projects = server.modrinth_projects or []
    combined_projects = list(set(existing_projects + new_projects))

    # Update server
    server.modrinth_projects = combined_projects
    await db.commit()
    await db.refresh(server)

    return JSONResponse(
        content={
            "message": f"Imported {len(new_projects)} projects from collection",
            "projects": combined_projects,
            "new_count": len(new_projects),
            "total_count": len(combined_projects),
        }
    )


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
    try:
        pod_name: str = await start_container(
            server_name=server.name,
            server_id=server.id,
            game_version=server.game_version,
            loader=server.loader,
            modrinth_projects=server.modrinth_projects,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(
        content={"pod": {"name": pod_name, "namespace": "minecraft"}}, status_code=201
    )


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


@router.get("/{server_id}/logs")
async def get_server_logs(server_id: str):
    """
    Stream logs from a Minecraft server pod in real-time

    Note: This endpoint doesn't use a database session to avoid holding
    connections during long-running streams. Server validation happens
    in the stream function via Kubernetes API.
    """
    try:
        return StreamingResponse(
            stream_server_logs(server_id, tail_lines=100),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e))
