"""
fix_project_types.py

One-time script to update existing modrinth_projects with correct types from Modrinth API.

Run with: python -m scripts.fix_project_types

This script:
1. Fetches all servers with modrinth_projects
2. For each project, fetches metadata from Modrinth API to get correct project_type
3. Updates the database with corrected types
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from fourdrinier.db.database import get_async_session_context
from fourdrinier.db.models import Server
from fourdrinier.services.modrinth_client import get_multiple_projects_metadata


async def fix_project_types():
    """Update all servers' modrinth_projects with correct types from Modrinth API."""

    async with get_async_session_context() as db:
        # Fetch all servers
        result = await db.execute(select(Server))
        servers = result.scalars().all()

        total_servers = len(servers)
        total_projects_fixed = 0

        print(f"Found {total_servers} servers")

        for i, server in enumerate(servers, 1):
            if not server.modrinth_projects:
                print(f"[{i}/{total_servers}] Server '{server.name}': No projects, skipping")
                continue

            projects = server.modrinth_projects

            # Extract project IDs
            project_ids = []
            for entry in projects:
                if isinstance(entry, str):
                    project_ids.append(entry)
                elif isinstance(entry, dict):
                    project_id = entry.get("id")
                    if project_id:
                        project_ids.append(project_id)

            if not project_ids:
                print(f"[{i}/{total_servers}] Server '{server.name}': No valid project IDs, skipping")
                continue

            print(f"[{i}/{total_servers}] Server '{server.name}': Fetching metadata for {len(project_ids)} projects...")

            # Fetch metadata from Modrinth
            projects_metadata = await get_multiple_projects_metadata(project_ids)

            # Update projects with correct types
            updated_projects = []
            projects_fixed = 0

            for entry in projects:
                if isinstance(entry, str):
                    # Old format: convert to new format with correct type
                    metadata = projects_metadata.get(entry)
                    project_type = metadata.get("project_type", "mod") if metadata else "mod"
                    updated_projects.append({
                        "id": entry,
                        "type": project_type
                    })
                    if metadata:
                        old_type = "mod"
                        if project_type != old_type:
                            print(f"  - {entry}: {old_type} → {project_type}")
                            projects_fixed += 1
                    else:
                        print(f"  - {entry}: metadata not found, defaulting to mod")

                elif isinstance(entry, dict):
                    # New format: update type if needed
                    project_id = entry.get("id")
                    old_type = entry.get("type", "mod")

                    if project_id:
                        metadata = projects_metadata.get(project_id)
                        correct_type = metadata.get("project_type", "mod") if metadata else "mod"

                        updated_projects.append({
                            "id": project_id,
                            "type": correct_type
                        })

                        if metadata and correct_type != old_type:
                            print(f"  - {project_id}: {old_type} → {correct_type}")
                            projects_fixed += 1
                        elif not metadata:
                            print(f"  - {project_id}: metadata not found, keeping {old_type}")
                    else:
                        # Invalid entry, keep as-is
                        updated_projects.append(entry)

            # Update server
            if projects_fixed > 0:
                server.modrinth_projects = updated_projects
                total_projects_fixed += projects_fixed
                print(f"  ✓ Fixed {projects_fixed} projects")
            else:
                print(f"  ✓ All types already correct")

        # Commit all changes
        await db.commit()

        print(f"\n{'='*60}")
        print(f"SUMMARY:")
        print(f"  Servers processed: {total_servers}")
        print(f"  Projects fixed: {total_projects_fixed}")
        print(f"{'='*60}")


if __name__ == "__main__":
    print("Starting project type fix script...")
    print("This will fetch metadata from Modrinth API and update project types.\n")

    asyncio.run(fix_project_types())

    print("\nDone! All project types have been updated.")
