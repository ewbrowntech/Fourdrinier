"""
servers.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Endpoints for interacting with server objects.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import os
import shutil
from pathlib import Path

from docker.errors import NotFound
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
from fourdrinier.db.session import get_db
from fourdrinier.dependencies.deploy.start_container import start_container
from fourdrinier.dependencies.deploy.start_container import stop_container


router = APIRouter()


@router.post("/", status_code=201, response_model=ServerResponse)
async def create_server(server_input: ServerCreate, db: AsyncSession = Depends(get_db)) -> Server:
    """
    Create a new server
    """
    server: Server = await crud.create_server(db, server_input)
    return server


@router.get("/", status_code=200, response_model=list[ServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)) -> list[Server]:
    """
    List all servers
    """
    servers: list[Server] = await crud.list_servers(db)
    return servers


@router.get("/{server_id}", status_code=200, response_model=ServerResponse)
async def get_server(server_id: str, db: AsyncSession = Depends(get_db)) -> Server:
    """
    Get a server by ID
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.delete("/{server_id}", status_code=200)
async def delete_server(server_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Get a server by ID
    """
    # Stop the server container
    try:
        image_name: str = f"fourdrinier-server-{server_id}"
        await stop_container(image_name)
    except NotFound:
        pass

    # Remove the server's storage directory
    storage_path: Path = Path(f"/storage/{server_id}")
    if storage_path.exists() and storage_path.is_dir():
        shutil.rmtree(storage_path, ignore_errors=True)

    # Remove the server from the database
    try:
        await crud.delete_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    return


@router.post("/{server_id}/start", status_code=201)
async def start_server(server_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Start a server
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Server storage path
    storage_path: Path = Path(f"/storage/{server.id}")
    storage_path.mkdir(exist_ok=True)
    host_storage_path: str = f"{os.getenv('STORAGE_PATH')}/{server.id}"

    # Start the server container'
    image_name: str = f"fourdrinier-server-{server.id}"
    container_id: str = await start_container(image_name, host_storage_path)

    return JSONResponse(content={"container": {"id": container_id, "name": image_name}})


@router.put("/{server_id}/stop", status_code=200)
async def stop_server(server_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Stop a server
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Start the server container'
    image_name: str = f"fourdrinier-server-{server.id}"
    await stop_container(image_name)

    return JSONResponse(content={"message": "Server stopped"})
