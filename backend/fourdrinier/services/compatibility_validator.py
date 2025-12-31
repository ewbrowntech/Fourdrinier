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
    metadata: dict, game_version: str, loader: str
) -> tuple[bool, list[str]]:
    """
    Check if a single project is compatible with given game version and loader.

    Args:
        metadata: Project metadata dict with game_versions and loaders
        game_version: Target Minecraft version (e.g., "1.20.1")
        loader: Target loader (e.g., "fabric")

    Returns:
        Tuple of (compatible: bool, warnings: list[str])
    """
    warnings = []

    # Check game version compatibility
    supported_versions = metadata.get("game_versions", [])
    if game_version not in supported_versions:
        warnings.append(
            f"No version available for Minecraft {game_version}. "
            f"Supported: {', '.join(supported_versions[:5])}"
            + ("..." if len(supported_versions) > 5 else "")
        )

    # Check loader compatibility (case-insensitive)
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

    project_ids = list(server.modrinth_projects or [])
    server_game_version = server.game_version
    server_loader = server.loader
    if not project_ids:
        return {
            "compatible": True,
            "warnings": [],
            "incompatible_projects": [],
        }

    # Fetch metadata for all projects from Modrinth API
    projects_metadata = await get_multiple_projects_metadata(project_ids)

    incompatible_projects = []
    all_warnings = []

    for project_id in project_ids:
        metadata = projects_metadata.get(project_id)

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

        # Check compatibility
        compatible, warnings = check_project_compatibility(
            metadata, server_game_version, server_loader
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
