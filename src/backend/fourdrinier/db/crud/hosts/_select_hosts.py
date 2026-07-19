"""
_select_hosts.py

Build statements that eagerly load complete host aggregates.
"""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from fourdrinier.db.models import Host


def select_hosts() -> Select[tuple[Host]]:
    """Build a statement that selects complete host aggregates.

    Returns:
        A host selection statement with provider details eagerly loaded.
    """
    statement: Select[tuple[Host]] = select(Host).options(
        selectinload(Host.docker_details),
        selectinload(Host.kubernetes_details),
    )
    return statement


__all__: list[str] = ["select_hosts"]
