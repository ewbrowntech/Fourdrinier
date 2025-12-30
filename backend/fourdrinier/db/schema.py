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
