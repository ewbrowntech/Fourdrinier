"""
models.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Models for database tables and relationships

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from .session import Base


class Server(Base):
    __tablename__ = "servers"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True, default="My Server")
    loader: Mapped[str]
    game_version: Mapped[str]
    modrinth_projects: Mapped[list[dict] | None] = mapped_column(JSON, default=None)

    # Per-server resource allocation (nullable - falls back to global config)
    cpu_request: Mapped[str | None] = mapped_column(default=None)
    cpu_limit: Mapped[str | None] = mapped_column(default=None)
    memory_request: Mapped[str | None] = mapped_column(default=None)
    memory_limit: Mapped[str | None] = mapped_column(default=None)
    pvc_size: Mapped[str | None] = mapped_column(default=None)
