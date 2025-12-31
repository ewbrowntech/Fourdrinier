"""
compatibility_validator.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Service for validating Modrinth project compatibility with server game version and loader

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from fourdrinier.db.models import Server
from fourdrinier.services.modrinth_client import get_multiple_projects_metadata

logger = logging.getLogger(__name__)


def check_project_compatibility(
    metadata: dict, game_version: str, loader: str, project_type: str = "mod"
) -> tuple[bool, list[str]]:
    """
    Check if a single project is compatible with given game version and loader.

    Loader checking is only performed for mods. Other project types (datapack, shader,
    resourcepack, plugin) only require game version compatibility.

    Args:
        metadata: Project metadata dict with game_versions and loaders
        game_version: Target Minecraft version (e.g., "1.20.1")
        loader: Target loader (e.g., "fabric")
        project_type: Project type (mod, datapack, shader, resourcepack, plugin)

    Returns:
        Tuple of (compatible: bool, warnings: list[str])
    """
    warnings = []

    # Check game version compatibility (required for ALL project types)
    supported_versions = metadata.get("game_versions", [])
    if game_version not in supported_versions:
        warnings.append(
            f"No version available for Minecraft {game_version}. "
            f"Supported: {', '.join(supported_versions[:5])}"
            + ("..." if len(supported_versions) > 5 else "")
        )

    # Check loader compatibility (ONLY for mods)
    # Datapacks, shaders, resourcepacks, and plugins are loader-agnostic
    if project_type == "mod":
        supported_loaders = [l.lower() for l in metadata.get("loaders", [])]
        if loader.lower() not in supported_loaders:
            warnings.append(
                f"Not available for {loader} loader. "
                f"Supported: {', '.join(metadata.get('loaders', []))}"
            )

    compatible = len(warnings) == 0
    return compatible, warnings


async def validate_server_modrinth_projects(
    server: Server, db: AsyncSession
) -> dict:
    """
    Validate all modrinth_projects against server's game_version and loader.

    Args:
        server: Server object with modrinth_projects, game_version, loader
        db: Database session for refreshing server state

    Returns:
        dict with keys:
            - compatible (bool): True if ALL projects compatible
            - warnings (list[str]): List of warning messages
            - incompatible_projects (list[dict]): Details about incompatible projects
    """
    state = inspect(server)
    if state.persistent:
        await db.refresh(server)

    project_list = server.modrinth_projects or []
    server_game_version = server.game_version
    server_loader = server.loader

    if not project_list:
        return {
            "compatible": True,
            "warnings": [],
            "incompatible_projects": [],
        }

    # Extract project IDs (handle both old and new formats)
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

    incompatible_projects = []
    all_warnings = []

    for project_id in project_ids:
        metadata = projects_metadata.get(project_id)
        project_type = project_types.get(project_id, "mod")

        if metadata is None:
            # Project not found
            warning_msg = f"{project_id}: Project not found on Modrinth"
            all_warnings.append(warning_msg)
            incompatible_projects.append({
                "project_id": project_id,
                "title": project_id,
                "reason": "Project not found on Modrinth",
                "supported_versions": [],
                "supported_loaders": [],
            })
            continue

        # Check compatibility (with project type awareness)
        compatible, warnings = check_project_compatibility(
            metadata, server_game_version, server_loader, project_type
        )

        if not compatible:
            title = metadata.get("title", project_id)
            reason = "; ".join(warnings)
            warning_msg = f"{title}: {reason}"
            all_warnings.append(warning_msg)

            incompatible_projects.append({
                "project_id": project_id,
                "title": title,
                "reason": reason,
                "supported_versions": metadata.get("game_versions", []),
                "supported_loaders": metadata.get("loaders", []),
            })

    all_compatible = len(incompatible_projects) == 0

    return {
        "compatible": all_compatible,
        "warnings": all_warnings,
        "incompatible_projects": incompatible_projects,
    }
