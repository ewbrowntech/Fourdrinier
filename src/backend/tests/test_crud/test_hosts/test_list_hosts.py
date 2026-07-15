"""
test_list_hosts.py

Integration tests for listing provider-neutral host aggregates.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from fourdrinier.db.crud.hosts.list_hosts import list_hosts
from fourdrinier.db.models import Host
from fourdrinier.hosts.types import HostType


@pytest.mark.parametrize(
    ("host_type", "expected_names"),
    [
        pytest.param(None, ["alpha-kubernetes", "zulu-docker"], id="all"),
        pytest.param(HostType.DOCKER, ["zulu-docker"], id="docker"),
        pytest.param(HostType.KUBERNETES, ["alpha-kubernetes"], id="kubernetes"),
    ],
)
async def test_list_hosts_001_nominal_hosts_are_ordered_and_filtered(
    app: FastAPI,
    docker_host_factory: Callable[[str], Host],
    kubernetes_host_factory: Callable[[str], Host],
    host_type: HostType | None,
    expected_names: list[str],
) -> None:
    """Test 001 - Nominal
    Condition: Docker and Kubernetes hosts exist and an optional provider filter is supplied
    Result: Matching hosts are returned in deterministic name order with details loaded
    """
    # Arrange
    session_factory: async_sessionmaker[AsyncSession] = app.state.session_factory
    docker_host: Host = docker_host_factory("zulu-docker")
    kubernetes_host: Host = kubernetes_host_factory("alpha-kubernetes")
    async with session_factory() as session:
        session.add_all([docker_host, kubernetes_host])
        await session.commit()
        session.expunge_all()

        # Act
        loaded: list[Host] = await list_hosts(session, host_type)

    # Assert
    assert [host.name for host in loaded] == expected_names
    for host in loaded:
        if host.type is HostType.DOCKER:
            assert host.docker_details is not None
        else:
            assert host.kubernetes_details is not None
