"""
servers.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Endpoints for interacting with server objects.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import logging
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from fourdrinier.db import crud
from fourdrinier.db.models import Server
from fourdrinier.db.schema import ServerCreate
from fourdrinier.db.schema import ServerResponse
from fourdrinier.db.schema import ServerUpdate
from fourdrinier.db.schema import ModrinthProjectEnriched
from fourdrinier.db.schema import ModrinthProjectInfo
from fourdrinier.db.schema import ModrinthProjectLookupRequest
from fourdrinier.db.schema import ImportCollectionResponse
from fourdrinier.db.schema import IncompatibleProject
from fourdrinier.db.session import get_db
from fourdrinier.dependencies.deploy.start_container import delete_server_resources
from fourdrinier.dependencies.deploy.start_container import get_server_status
from fourdrinier.dependencies.deploy.start_container import start_container
from fourdrinier.dependencies.deploy.start_container import stop_container
from fourdrinier.dependencies.deploy.start_container import stream_server_logs
from fourdrinier.services.modrinth_client import get_collection_projects
from fourdrinier.services.modrinth_client import get_multiple_projects_metadata
from fourdrinier.services.compatibility_validator import validate_server_modrinth_projects


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
        "cpu_request": server.cpu_request,
        "cpu_limit": server.cpu_limit,
        "memory_request": server.memory_request,
        "memory_limit": server.memory_limit,
        "pvc_size": server.pvc_size,
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
        status = await get_server_status(server.id, server.name)
        server_dict = {
            "id": server.id,
            "name": server.name,
            "loader": server.loader,
            "game_version": server.game_version,
            "modrinth_projects": server.modrinth_projects,
            "status": status,
            "cpu_request": server.cpu_request,
            "cpu_limit": server.cpu_limit,
            "memory_request": server.memory_request,
            "memory_limit": server.memory_limit,
            "pvc_size": server.pvc_size,
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
    status = await get_server_status(server.id, server.name)
    return {
        "id": server.id,
        "name": server.name,
        "loader": server.loader,
        "game_version": server.game_version,
        "modrinth_projects": server.modrinth_projects,
        "status": status,
        "cpu_request": server.cpu_request,
        "cpu_limit": server.cpu_limit,
        "memory_request": server.memory_request,
        "memory_limit": server.memory_limit,
        "pvc_size": server.pvc_size,
    }


@router.put("/{server_id}", status_code=200, response_model=ServerResponse)
async def update_server(
    server_id: str, server_update: ServerUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Update a server's details.
    Resource changes (CPU/memory) only allowed when server is stopped or created.
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Check if resource fields are being updated
    resource_fields = ["cpu_request", "cpu_limit", "memory_request", "memory_limit"]
    update_dict = server_update.model_dump(exclude_unset=True)
    resource_update_attempted = any(field in update_dict for field in resource_fields)

    # If resources are being updated, validate server is stopped
    if resource_update_attempted:
        status = await get_server_status(server.id, server.name)
        if status not in ["stopped", "created"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot update resources while server is {status}. Please stop the server first.",
            )

    # Proceed with update
    server = await crud.update_server(db, server_id, server_update)

    # Return response with all fields
    status = await get_server_status(server.id, server.name)
    return {
        "id": server.id,
        "name": server.name,
        "loader": server.loader,
        "game_version": server.game_version,
        "modrinth_projects": server.modrinth_projects,
        "status": status,
        "cpu_request": server.cpu_request,
        "cpu_limit": server.cpu_limit,
        "memory_request": server.memory_request,
        "memory_limit": server.memory_limit,
        "pvc_size": server.pvc_size,
    }


@router.get("/{server_id}/modrinth-projects", status_code=200, response_model=list[ModrinthProjectEnriched])
async def get_server_modrinth_projects(
    server_id: str, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """
    Get enriched metadata for all Modrinth projects on a server.
    Includes compatibility validation against server's game version and loader.
    """
    # Get server
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    project_list = server.modrinth_projects or []
    # If no modrinth_projects, return empty list
    if not project_list:
        return []

    # Extract project IDs and types (handle both old and new formats)
    project_ids = []
    project_types = {}  # Map project_id -> project_type

    for project_entry in project_list:
        if isinstance(project_entry, str):
            # Old format: simple string
            project_ids.append(project_entry)
            project_types[project_entry] = "mod"  # Default for backward compatibility
        elif isinstance(project_entry, dict):
            # New format: {"id": "...", "type": "..."}
            project_id = project_entry.get("id")
            project_type = project_entry.get("type", "mod")
            if project_id:
                project_ids.append(project_id)
                project_types[project_id] = project_type

    # Fetch metadata for all projects from Modrinth API
    projects_metadata = await get_multiple_projects_metadata(project_ids)

    # Validate compatibility and build enriched response
    enriched_projects = []

    for project_id in project_ids:
        metadata = projects_metadata.get(project_id)
        project_type = project_types.get(project_id, "mod")

        if metadata is None:
            # Project not found
            enriched_projects.append({
                "project_id": project_id,
                "title": project_id,
                "description": "Project not found on Modrinth",
                "icon_url": None,
                "compatible": False,
                "warnings": ["Project not found on Modrinth"],
                "project_type": project_type,
            })
            continue

        # Check compatibility (with project type awareness)
        from fourdrinier.services.compatibility_validator import check_project_compatibility
        compatible, warnings = check_project_compatibility(
            metadata, server.game_version, server.loader, project_type
        )

        enriched_projects.append({
            "project_id": project_id,
            "title": metadata.get("title", project_id),
            "description": metadata.get("description", ""),
            "icon_url": metadata.get("icon_url"),
            "compatible": compatible,
            "warnings": warnings,
            "project_type": project_type,  # Include type from database
        })

    return enriched_projects


@router.post("/modrinth-projects/lookup", status_code=200, response_model=list[ModrinthProjectInfo])
async def lookup_modrinth_projects(
    payload: ModrinthProjectLookupRequest, db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """
    Resolve Modrinth project IDs/slugs to metadata without server compatibility checks.
    """
    project_ids = list(payload.project_ids or [])
    if not project_ids:
        return []

    projects_metadata = await get_multiple_projects_metadata(project_ids)
    resolved_projects: list[dict] = []

    for project_id in project_ids:
        metadata = projects_metadata.get(project_id)
        if metadata is None:
            resolved_projects.append({
                "project_id": project_id,
                "title": project_id,
                "description": "Project not found on Modrinth",
                "icon_url": None,
            })
            continue

        resolved_projects.append({
            "project_id": project_id,
            "title": metadata.get("title", project_id),
            "description": metadata.get("description", ""),
            "icon_url": metadata.get("icon_url"),
        })

    return resolved_projects


@router.post("/{server_id}/import-collection", status_code=200, response_model=ImportCollectionResponse)
async def import_modrinth_collection(
    server_id: str, collection_url: str, db: AsyncSession = Depends(get_db)
) -> ImportCollectionResponse:
    """
    Import Modrinth projects from a collection URL and append to server's project list.
    Validates compatibility but allows all projects to be added with warnings.
    """
    # Get the server
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Fetch projects from Modrinth collection
    try:
        new_project_ids = await get_collection_projects(collection_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch collection from Modrinth: {str(e)}")

    # Fetch metadata to auto-detect project types
    projects_metadata = await get_multiple_projects_metadata(new_project_ids)

    # Helper function to select best project type based on loader
    def select_best_project_type(project_types: list[str], loader: str) -> str:
        """
        Select the best project type based on available types and loader.

        If a project is available as both mod and datapack, prefer mod for Fabric/Forge loaders.
        """
        if not project_types:
            return "mod"

        # If only one type, use it
        if len(project_types) == 1:
            return project_types[0]

        # If multiple types and loader is Fabric/Forge, prefer mod over datapack
        if loader.lower() in ["fabric", "forge"] and "mod" in project_types:
            return "mod"

        # Otherwise, use first type
        return project_types[0]

    # Convert to structured format with types
    new_projects_structured = []
    for project_id in new_project_ids:
        metadata = projects_metadata.get(project_id)
        project_type = "mod"  # Default

        if metadata:
            # Use smart type selection if project_types array is available
            project_types = metadata.get("project_types", [metadata.get("project_type", "mod")])
            project_type = select_best_project_type(project_types, server.loader)

        new_projects_structured.append({
            "id": project_id,
            "type": project_type
        })

    # Merge with existing projects (deduplicate by project ID)
    existing_projects = server.modrinth_projects or []

    # Convert existing to dict for deduplication
    existing_dict = {}
    for entry in existing_projects:
        if isinstance(entry, str):
            existing_dict[entry] = {"id": entry, "type": "mod"}
        elif isinstance(entry, dict):
            project_id = entry.get("id")
            if project_id:
                existing_dict[project_id] = entry

    # Add new projects (overwrites if same ID)
    for project in new_projects_structured:
        existing_dict[project["id"]] = project

    # Convert back to list
    combined_projects = list(existing_dict.values())

    # Update server
    server.modrinth_projects = combined_projects
    await db.commit()
    await db.refresh(server)

    # Validate compatibility (informative only, doesn't block)
    validation_result = await validate_server_modrinth_projects(server, db)

    return ImportCollectionResponse(
        message=f"Imported {len(new_projects_structured)} projects from collection",
        projects=combined_projects,
        new_count=len(new_projects_structured),
        total_count=len(combined_projects),
        warnings=validation_result["warnings"],
        incompatible_projects=[
            IncompatibleProject(**proj)
            for proj in validation_result["incompatible_projects"]
        ],
    )


@router.delete("/{server_id}", status_code=200)
async def delete_server(server_id: str, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a server and all its Kubernetes resources
    """
    # Get server before deletion to pass name for logging
    try:
        server: Server = await crud.get_server(db, server_id)
        server_name = server.name
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Delete Kubernetes resources (Pod, PVC, Service)
    await delete_server_resources(server_id, server_name)

    # Remove the server from the database
    await crud.delete_server(db, server_id)

    return


@router.post("/{server_id}/start", status_code=201)
async def start_server(server_id: str, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """
    Start a Minecraft server in Kubernetes.
    For Fabric servers, validates mod compatibility before starting.
    """
    try:
        server: Server = await crud.get_server(db, server_id)
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Server not found")

    # Start the server in Kubernetes (includes compatibility validation)
    try:
        pod_name: str = await start_container(
            server_name=server.name,
            server_id=server.id,
            game_version=server.game_version,
            loader=server.loader,
            modrinth_projects=server.modrinth_projects,
            db=db,  # Pass database session for validation
            # Pass per-server resources
            cpu_request=server.cpu_request,
            cpu_limit=server.cpu_limit,
            memory_request=server.memory_request,
            memory_limit=server.memory_limit,
            pvc_size=server.pvc_size,
        )
    except HTTPException:
        # Re-raise HTTP exceptions (compatibility validation failures)
        raise
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
