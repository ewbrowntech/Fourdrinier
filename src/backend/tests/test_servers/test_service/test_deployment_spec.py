"""
test_deployment_spec.py

Unit tests for ServerService.deployment_spec.
"""

from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, Mock

from fourdrinier.db.models import Server
from fourdrinier.servers import ServerRuntime
from fourdrinier.servers.deployment import DeploymentSpec
from fourdrinier.servers.service import ServerService
from tests.test_servers.test_service.support import (
    SERVER_ID,
    CrudMocks,
    ServiceDependencies,
    server,
    service_dependencies,
)


async def test_server_service_deployment_spec_001_nominal_runtime_translates_server(
    crud: CrudMocks,
) -> None:
    """Test 001 - Nominal
    Condition: A saved server has a registered runtime adapter
    Result: The service returns the adapter's provider-neutral deployment specification
    """
    # Arrange
    dependencies: ServiceDependencies = service_dependencies()
    service: ServerService = dependencies.service
    session: AsyncMock = dependencies.session
    persisted: Server = server()
    specification: DeploymentSpec = cast(DeploymentSpec, Mock(spec=DeploymentSpec))
    crud.get_server.return_value = persisted
    dependencies.runtime.deployment_spec.return_value = specification

    # Act
    result: DeploymentSpec = await service.deployment_spec(SERVER_ID)

    # Assert
    assert result is specification
    crud.get_server.assert_awaited_once_with(session, SERVER_ID)
    dependencies.runtimes.for_runtime.assert_called_once_with(ServerRuntime.PUMPKIN)
    dependencies.runtime.deployment_spec.assert_called_once_with(persisted)
