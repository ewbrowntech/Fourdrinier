"""
modrinth_client.py

Modrinth API client for fetching mod/plugin collections

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import asyncio
import httpx
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
        dict with keys: title, description, icon_url, game_versions, loaders
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

            return {
                "title": data.get("title", project_id),
                "description": data.get("description", ""),
                "icon_url": data.get("icon_url"),
                "game_versions": data.get("game_versions", []),
                "loaders": data.get("loaders", []),
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
    Batch fetch project metadata for multiple projects with rate limit awareness.

    Uses concurrent requests with a semaphore to respect rate limits.
    Modrinth rate limit: ~300 requests/5 minutes, so we limit concurrent requests.

    Args:
        project_ids: List of Modrinth project slugs/IDs

    Returns:
        Dict mapping project_id -> metadata dict
        Failed/not found projects will have None as value
    """
    # Limit concurrent requests to avoid rate limiting (max 5 at a time)
    semaphore = asyncio.Semaphore(5)

    async def fetch_with_semaphore(project_id: str) -> tuple[str, dict | None]:
        async with semaphore:
            try:
                # Small delay between requests to be respectful
                await asyncio.sleep(0.1)
                metadata = await get_project_metadata(project_id)
                return (project_id, metadata)
            except Exception as e:
                logger.error(f"Failed to fetch metadata for {project_id}: {e}")
                return (project_id, None)

    # Fetch all projects concurrently (but limited by semaphore)
    results = await asyncio.gather(
        *[fetch_with_semaphore(pid) for pid in project_ids],
        return_exceptions=True
    )

    # Build result dictionary
    metadata_dict = {}
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Exception during batch fetch: {result}")
            continue
        project_id, metadata = result
        metadata_dict[project_id] = metadata

    return metadata_dict
