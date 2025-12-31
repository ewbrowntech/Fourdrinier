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
from pydantic import field_validator


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

    # Per-server resource allocation (optional, uses global defaults if not specified)
    cpu_request: str | None = Field(
        default=None,
        title="CPU Request",
        description="Kubernetes CPU request (e.g., '1000m' or '1')",
        json_schema_extra={"examples": ["1000m", "2"]},
    )
    cpu_limit: str | None = Field(
        default=None,
        title="CPU Limit",
        description="Kubernetes CPU limit (e.g., '2000m' or '2')",
        json_schema_extra={"examples": ["2000m", "4"]},
    )
    memory_request: str | None = Field(
        default=None,
        title="Memory Request",
        description="Kubernetes memory request (e.g., '2Gi' or '512Mi')",
        json_schema_extra={"examples": ["2Gi", "512Mi"]},
    )
    memory_limit: str | None = Field(
        default=None,
        title="Memory Limit",
        description="Kubernetes memory limit (e.g., '4Gi' or '1024Mi')",
        json_schema_extra={"examples": ["4Gi", "1024Mi"]},
    )
    pvc_size: str | None = Field(
        default=None,
        title="PVC Size",
        description="Persistent Volume Claim size (e.g., '5Gi' or '10Gi')",
        json_schema_extra={"examples": ["5Gi", "10Gi"]},
    )

    @field_validator("cpu_request", "cpu_limit")
    @classmethod
    def validate_cpu(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Validate format: digits followed by optional 'm' or just digits
        import re

        if not re.match(r"^\d+m?$", v):
            raise ValueError('CPU must be in format "1000m" or "1"')
        return v

    @field_validator("memory_request", "memory_limit", "pvc_size")
    @classmethod
    def validate_memory(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Validate format: digits followed by Mi or Gi
        import re

        if not re.match(r"^\d+(Mi|Gi)$", v):
            raise ValueError('Memory/Storage must be in format "2Gi" or "512Mi"')
        return v


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

    # Resource allocation (can only be updated when server is stopped)
    # Note: pvc_size NOT included - cannot be changed after creation
    cpu_request: str | None = Field(
        default=None,
        title="CPU Request",
        description="Kubernetes CPU request (e.g., '1000m' or '1')",
        json_schema_extra={"examples": ["1000m", "2"]},
    )
    cpu_limit: str | None = Field(
        default=None,
        title="CPU Limit",
        description="Kubernetes CPU limit (e.g., '2000m' or '2')",
        json_schema_extra={"examples": ["2000m", "4"]},
    )
    memory_request: str | None = Field(
        default=None,
        title="Memory Request",
        description="Kubernetes memory request (e.g., '2Gi' or '512Mi')",
        json_schema_extra={"examples": ["2Gi", "512Mi"]},
    )
    memory_limit: str | None = Field(
        default=None,
        title="Memory Limit",
        description="Kubernetes memory limit (e.g., '4Gi' or '1024Mi')",
        json_schema_extra={"examples": ["4Gi", "1024Mi"]},
    )

    @field_validator("cpu_request", "cpu_limit")
    @classmethod
    def validate_cpu(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re

        if not re.match(r"^\d+m?$", v):
            raise ValueError('CPU must be in format "1000m" or "1"')
        return v

    @field_validator("memory_request", "memory_limit")
    @classmethod
    def validate_memory(cls, v: str | None) -> str | None:
        if v is None:
            return v
        import re

        if not re.match(r"^\d+(Mi|Gi)$", v):
            raise ValueError('Memory must be in format "2Gi" or "512Mi"')
        return v


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

    # Resource allocation fields (for display)
    cpu_request: str | None = None
    cpu_limit: str | None = None
    memory_request: str | None = None
    memory_limit: str | None = None
    pvc_size: str | None = None


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
