"""
modrinth_client.py

Modrinth API client for fetching mod/plugin collections

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import httpx
import re
from typing import List


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
