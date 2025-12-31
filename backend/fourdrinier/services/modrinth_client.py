"""
modrinth_client.py

Modrinth API client for fetching mod/plugin collections

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import asyncio
import httpx
import json
import re
from typing import List
import logging

logger = logging.getLogger(__name__)


def extract_collection_id(collection_url: str) -> str:
    """
    Extract collection ID from a Modrinth collection URL.

    Supports both full URLs and bare IDs:
    - https://modrinth.com/collection/Ab0s6egg -> Ab0s6egg
    - Ab0s6egg -> Ab0s6egg

    Args:
        collection_url: Modrinth collection URL or ID

    Returns:
        Collection ID string

    Raises:
        ValueError: If URL format is invalid
    """
    # If it's already just an ID (no slashes or protocol), return as-is
    if not ("/" in collection_url or ":" in collection_url):
        return collection_url

    # Extract ID from URL: https://modrinth.com/collection/Ab0s6egg
    match = re.search(r'/collection/([a-zA-Z0-9]+)', collection_url)
    if match:
        return match.group(1)

    raise ValueError(f"Invalid Modrinth collection URL: {collection_url}")


async def get_collection_projects(collection_id_or_url: str) -> List[str]:
    """
    Fetch project list from a Modrinth collection.

    Args:
        collection_id_or_url: Modrinth collection ID or full URL

    Returns:
        List of project slugs/IDs

    Raises:
        ValueError: If collection URL is invalid
        httpx.HTTPStatusError: If Modrinth API request fails
    """
    # Extract ID from URL if needed
    collection_id = extract_collection_id(collection_id_or_url)

    # Call Modrinth API v3
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.modrinth.com/v3/collection/{collection_id}",
            headers={
                "User-Agent": "Fourdrinier/1.0 (minecraft server manager)"
            },
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        return data.get("projects", [])


async def get_project_metadata(project_id: str) -> dict | None:
    """
    Fetch project metadata from Modrinth API v3.

    Args:
        project_id: Modrinth project slug or ID

    Returns:
        dict with keys: title, description, icon_url, game_versions, loaders, project_type
        None if project not found or API error

    Raises:
        httpx.HTTPStatusError: If Modrinth API request fails (except 404)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.modrinth.com/v3/project/{project_id}",
                headers={
                    "User-Agent": "Fourdrinier/1.0 (minecraft server manager)"
                },
                timeout=10.0
            )

            if response.status_code == 404:
                logger.warning(f"Project {project_id} not found on Modrinth")
                return None

            response.raise_for_status()
            data = response.json()

            # Extract project_type from project_types array (Modrinth v3 returns an array)
            project_types = data.get("project_types", ["mod"])
            project_type = project_types[0] if project_types else "mod"

            # Modrinth v3 uses "name" not "title"
            title = data.get("name", project_id)

            return {
                "title": title,
                "description": data.get("description", ""),
                "icon_url": data.get("icon_url"),
                "game_versions": data.get("game_versions", []),
                "loaders": data.get("loaders", []),
                "project_type": project_type,
                "project_types": project_types,  # Include full array for smart type selection
            }
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching metadata for project {project_id}")
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:  # Rate limit
            logger.warning(f"Rate limited by Modrinth API for project {project_id}")
        raise


async def get_multiple_projects_metadata(project_ids: list[str]) -> dict[str, dict]:
    """
    Batch fetch project metadata for multiple projects using Modrinth's batch API.

    Uses Modrinth API v3 batch endpoint: GET /v3/projects?ids=["id1","id2",...]
    Batches requests in groups of 100 (Modrinth's limit per request).

    Args:
        project_ids: List of Modrinth project slugs/IDs

    Returns:
        Dict mapping project_id -> metadata dict
        Failed/not found projects will have None as value
    """
    if not project_ids:
        return {}

    metadata_dict = {}

    # Batch in groups of 100 (Modrinth API limit)
    batch_size = 100
    for i in range(0, len(project_ids), batch_size):
        batch = project_ids[i:i + batch_size]

        try:
            async with httpx.AsyncClient() as client:
                # Modrinth batch endpoint expects JSON array as query param
                ids_param = json.dumps(batch)

                response = await client.get(
                    f"https://api.modrinth.com/v3/projects",
                    params={"ids": ids_param},
                    headers={
                        "User-Agent": "Fourdrinier/1.0 (minecraft server manager)"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                projects_data = response.json()

                # Process each project in the batch response
                for project_data in projects_data:
                    project_id = project_data.get("id") or project_data.get("slug")

                    # Extract project_type from project_types array
                    project_types = project_data.get("project_types", ["mod"])
                    project_type = project_types[0] if project_types else "mod"

                    # Use "name" field (Modrinth v3)
                    title = project_data.get("name", project_id)

                    metadata_dict[project_id] = {
                        "title": title,
                        "description": project_data.get("description", ""),
                        "icon_url": project_data.get("icon_url"),
                        "game_versions": project_data.get("game_versions", []),
                        "loaders": project_data.get("loaders", []),
                        "project_type": project_type,
                        "project_types": project_types,
                    }

                # Mark any projects not in response as not found
                returned_ids = {p.get("id") or p.get("slug") for p in projects_data}
                for project_id in batch:
                    if project_id not in returned_ids and project_id not in metadata_dict:
                        metadata_dict[project_id] = None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"Rate limited by Modrinth API during batch fetch")
            logger.error(f"HTTP error fetching batch: {e}")
            # Mark all projects in failed batch as None
            for project_id in batch:
                if project_id not in metadata_dict:
                    metadata_dict[project_id] = None
        except Exception as e:
            logger.error(f"Error fetching batch: {e}")
            # Mark all projects in failed batch as None
            for project_id in batch:
                if project_id not in metadata_dict:
                    metadata_dict[project_id] = None

    return metadata_dict


async def get_project_versions(
    project_id: str,
    game_versions: list[str] | None = None,
    loaders: list[str] | None = None,
) -> list[dict]:
    """
    Fetch versions for a project from Modrinth API v2.

    Args:
        project_id: Modrinth project slug or ID
        game_versions: List of game versions to filter by (e.g., ["1.20.1"])
        loaders: List of loaders to filter by (e.g., ["fabric"])

    Returns:
        List of version objects sorted by date_published (newest first)
        Each version contains: id, name, version_number, files[], game_versions, loaders

    Raises:
        httpx.HTTPStatusError: If Modrinth API request fails
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {}
            if game_versions:
                params["game_versions"] = json.dumps(game_versions)
            if loaders:
                params["loaders"] = json.dumps(loaders)

            response = await client.get(
                f"https://api.modrinth.com/v2/project/{project_id}/version",
                params=params,
                headers={
                    "User-Agent": "Fourdrinier/1.0 (minecraft server manager)"
                },
                timeout=10.0
            )

            if response.status_code == 404:
                logger.warning(f"Project {project_id} not found on Modrinth")
                return []

            response.raise_for_status()
            versions = response.json()

            return versions
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching versions for project {project_id}")
        return []
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning(f"Rate limited by Modrinth API for project {project_id}")
        raise


async def get_latest_versions_batch(
    projects: list[dict],
    game_version: str,
    loader: str,
) -> dict[str, dict | None]:
    """
    Batch fetch latest compatible versions for multiple projects.

    Uses highly concurrent requests to efficiently fetch versions for many projects.
    Modrinth's API can handle high concurrency, so we use 100 concurrent requests
    for optimal performance with large modpacks.

    Args:
        projects: List of project dicts with 'id' and 'type' keys
        game_version: Target Minecraft version (e.g., "1.20.1")
        loader: Target loader (e.g., "fabric")

    Returns:
        Dict mapping project_id -> version dict (or None if not found)
        Version dict contains: files[], version_number, name, etc.
    """
    if not projects:
        return {}

    # Use high concurrency (100 at a time) - Modrinth can handle this
    # For 200 mods, this means only ~2 batches instead of 20
    semaphore = asyncio.Semaphore(100)

    async def fetch_latest_version(project: dict) -> tuple[str, dict | None]:
        """Fetch latest version for a single project"""
        project_id = project.get("id")
        project_type = project.get("type", "mod")

        async with semaphore:
            try:
                # For mods, filter by both loader and game version
                # For other types, only filter by game version (loader-agnostic)
                loaders = [loader] if project_type == "mod" else None

                versions = await get_project_versions(
                    project_id,
                    game_versions=[game_version],
                    loaders=loaders
                )

                if not versions:
                    logger.warning(f"No compatible versions found for {project_id}")
                    return (project_id, None)

                # Return the first (most recent) version
                latest_version = versions[0]
                return (project_id, latest_version)

            except Exception as e:
                logger.error(f"Failed to fetch version for {project_id}: {e}")
                return (project_id, None)

    # Fetch all versions concurrently (limited by semaphore)
    # With 100 concurrent requests, 200 mods takes ~2 seconds
    logger.info(f"Fetching {len(projects)} project versions with 100 concurrent requests...")
    results = await asyncio.gather(
        *[fetch_latest_version(project) for project in projects],
        return_exceptions=True
    )

    # Build result dictionary
    versions_dict = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception during batch version fetch: {result}")
            continue
        project_id, version = result
        versions_dict[project_id] = version

    successful = sum(1 for v in versions_dict.values() if v is not None)
    logger.info(f"Successfully fetched {successful}/{len(projects)} project versions")

    return versions_dict
