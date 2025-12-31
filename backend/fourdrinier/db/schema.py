"""
schema.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Schema for serialization and deserialization of data models.

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from pydantic import BaseModel
from pydantic import Field


class ServerCreate(BaseModel):
    name: str = Field(
        default="My Server",
        title="Server Name",
        description="The name of the server.",
        json_schema_extra={"examples": ["My Server"]},
    )
    loader: str = Field(
        default="paper",
        title="Loader",
        json_schema_extra={"examples": ["paper"]},
    )
    game_version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+$",
        title="Game Version",
        json_schema_extra={"examples": ["1.17.1"]},
    )
    modrinth_projects: list[str] | None = Field(
        default=None,
        title="Modrinth Projects",
        description="List of Modrinth project slugs/IDs for Fabric mod installation",
        json_schema_extra={"examples": [["lithium", "sodium", "fabric-api"]]},
    )


class ServerUpdate(BaseModel):
    name: str = Field(
        ...,
        title="Server Name",
        description="The name of the server.",
        json_schema_extra={"examples": ["My Server"]},
    )
    modrinth_projects: list[str] | None = Field(
        default=None,
        title="Modrinth Projects",
        description="List of Modrinth project slugs/IDs for Fabric mod installation",
        json_schema_extra={"examples": [["lithium", "sodium", "fabric-api"]]},
    )


class ServerResponse(BaseModel):
    id: str
    name: str
    loader: str
    game_version: str
    modrinth_projects: list[str] | None = None
    status: str = Field(
        default="created",
        title="Server Status",
        description="Current status of the server (running, pending, stopped, created, error)",
    )


class ModrinthProjectEnriched(BaseModel):
    """Enriched project metadata with compatibility information"""
    project_id: str
    title: str
    description: str
    icon_url: str | None = None
    compatible: bool
    warnings: list[str] = Field(default_factory=list)


class ModrinthProjectInfo(BaseModel):
    """Project metadata without compatibility validation"""
    project_id: str
    title: str
    description: str = ""
    icon_url: str | None = None


class ModrinthProjectLookupRequest(BaseModel):
    """Request payload for resolving Modrinth project IDs to metadata"""
    project_ids: list[str]


class IncompatibleProject(BaseModel):
    """Details about an incompatible project"""
    project_id: str
    title: str
    reason: str
    supported_versions: list[str]
    supported_loaders: list[str]


class ImportCollectionResponse(BaseModel):
    """Response for collection import with compatibility warnings"""
    message: str
    projects: list[str]
    new_count: int
    total_count: int
    warnings: list[str] = Field(default_factory=list)
    incompatible_projects: list[IncompatibleProject] = Field(default_factory=list)
