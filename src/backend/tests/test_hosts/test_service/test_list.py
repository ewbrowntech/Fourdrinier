"""
test_list.py

Unit tests for HostService.list.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from fourdrinier.db.models import Host
from fourdrinier.hosts import HostType
from fourdrinier.hosts.service import HostService
from tests.test_hosts.test_service.support import CrudMocks, host, service_dependencies


@pytest.mark.parametrize(
    "host_type",
    [
        pytest.param(None, id="all"),
        pytest.param(HostType.DOCKER, id="docker"),
        pytest.param(HostType.KUBERNETES, id="kubernetes"),
    ],
)
async def test_host_service_list_001_nominal_provider_filter_is_forwarded(
    host_type: HostType | None,
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A caller supplies an optional provider filter
    Result: The ordered matching aggregate list is returned unchanged
    """
    # Arrange
    service: HostService
    session: AsyncMock
    _drivers: Mock
    _secret_encryptor: Mock
    service, session, _drivers, _secret_encryptor = service_dependencies()
    hosts: list[Host] = [host()]
    crud.list_hosts.return_value = hosts

    # Act
    result: list[Host] = await service.list(host_type)

    # Assert
    assert result is hosts
    crud.list_hosts.assert_awaited_once_with(session, host_type)
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()
