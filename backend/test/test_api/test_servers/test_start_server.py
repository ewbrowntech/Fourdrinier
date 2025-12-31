"""
test_start_server.py

@Author: Ethan Brown - ethan@ewbrowntech.com

Test POST /servers/{server_id}/start

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from httpx import Response
from kubernetes.client.rest import ApiException
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.db.models import Server


async def test_start_server_000_nominal(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 000 - Nominal
    Conditions: Server exists in database, Kubernetes client mocked for success
    Result: HTTP 201 - Pod created with correct name and namespace
    """
    # Add a server to the database
    server = Server(id="test-server-1", name="Test Server", loader="paper", game_version="1.20.0")
    test_db.add(server)
    await test_db.commit()

    # Start the server
    response: Response = await client.post("servers/test-server-1/start")

    # Ensure the correct response is returned
    assert response.status_code == 201
    assert response.json() == {
        "pod": {"name": "minecraft-test-server-1", "namespace": "minecraft"}
    }

    # Verify Kubernetes resources were created
    mock_k8s_client.create_namespaced_persistent_volume_claim.assert_called_once()
    mock_k8s_client.create_namespaced_pod.assert_called_once()
    mock_k8s_client.create_namespaced_service.assert_called_once()

    # Verify Pod was created with correct configuration
    pod_call_args = mock_k8s_client.create_namespaced_pod.call_args
    pod_spec = pod_call_args[0][1]  # Second argument is the pod object
    assert pod_spec.metadata.name == "minecraft-test-server-1"
    assert pod_spec.spec.containers[0].image is not None
    assert any(env.name == "VERSION" and env.value == "1.20.0" for env in pod_spec.spec.containers[0].env)


async def test_start_server_001_nominal_with_modrinth_projects(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 001 - Nominal
    Conditions: Fabric server with Modrinth projects, Kubernetes client mocked
    Result: HTTP 201 - Pod created with MODRINTH_PROJECTS environment variable
    """
    # Add a Fabric server with Modrinth projects
    server = Server(
        id="test-server-2",
        name="Fabric Server",
        loader="fabric",
        game_version="1.20.1",
        modrinth_projects=["sodium", "lithium", "phosphor"],
    )
    test_db.add(server)
    await test_db.commit()

    # Start the server
    response: Response = await client.post("servers/test-server-2/start")

    # Ensure the correct response is returned
    assert response.status_code == 201
    assert "pod" in response.json()

    # Verify Pod was created with Modrinth environment variables
    pod_call_args = mock_k8s_client.create_namespaced_pod.call_args
    pod_spec = pod_call_args[0][1]
    env_vars = pod_spec.spec.containers[0].env

    # Check for MODRINTH_PROJECTS environment variable
    modrinth_projects_env = next((env for env in env_vars if env.name == "MODRINTH_PROJECTS"), None)
    assert modrinth_projects_env is not None
    assert modrinth_projects_env.value == "sodium,lithium,phosphor"

    # Check for MODRINTH_DOWNLOAD_DEPENDENCIES environment variable
    modrinth_deps_env = next(
        (env for env in env_vars if env.name == "MODRINTH_DOWNLOAD_DEPENDENCIES"), None
    )
    assert modrinth_deps_env is not None
    assert modrinth_deps_env.value == "required"


async def test_start_server_002_nominal_idempotent(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 002 - Nominal
    Conditions: Server exists, Pod already running (409 Conflict on creation)
    Result: HTTP 201 - Returns successfully (idempotent behavior)
    """
    # Add a server to the database
    server = Server(id="test-server-3", name="Running Server", loader="paper", game_version="1.20.0")
    test_db.add(server)
    await test_db.commit()

    # Mock Pod creation to return 409 Conflict (already exists)
    mock_k8s_client.create_namespaced_pod.side_effect = ApiException(status=409)

    # Start the server
    response: Response = await client.post("servers/test-server-3/start")

    # Should still return 201 (idempotent)
    assert response.status_code == 201
    assert "pod" in response.json()


async def test_start_server_003_anomalous_server_not_found(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 003 - Anomalous
    Conditions: Request to start non-existent server
    Result: HTTP 404 - "Server not found"
    """
    # Attempt to start a server that doesn't exist
    response: Response = await client.post("servers/nonexistent-server/start")

    # Ensure the correct error is returned
    assert response.status_code == 404
    assert response.json() == {"detail": "Server not found"}

    # Verify no Kubernetes resources were attempted
    mock_k8s_client.create_namespaced_persistent_volume_claim.assert_not_called()
    mock_k8s_client.create_namespaced_pod.assert_not_called()
    mock_k8s_client.create_namespaced_service.assert_not_called()


async def test_start_server_004_anomalous_pvc_creation_fails(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 004 - Anomalous
    Conditions: Server exists, Kubernetes PVC creation fails (non-409 error)
    Result: HTTP 500 - RuntimeError from start_container
    """
    # Add a server to the database
    server = Server(id="test-server-4", name="Failing Server", loader="paper", game_version="1.20.0")
    test_db.add(server)
    await test_db.commit()

    # Mock PVC creation to fail with a 500 error
    mock_k8s_client.create_namespaced_persistent_volume_claim.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )

    # Attempt to start the server
    response: Response = await client.post("servers/test-server-4/start")

    # Should return 500 error
    assert response.status_code == 500
    assert "detail" in response.json()

    # Verify Pod was not created
    mock_k8s_client.create_namespaced_pod.assert_not_called()


async def test_start_server_005_anomalous_pod_creation_fails(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 005 - Anomalous
    Conditions: Server exists, PVC succeeds, Pod creation fails
    Result: HTTP 500 - RuntimeError from start_container, PVC cleaned up
    """
    # Add a server to the database
    server = Server(id="test-server-5", name="Pod Fail Server", loader="paper", game_version="1.20.0")
    test_db.add(server)
    await test_db.commit()

    # Mock Pod creation to fail, but PVC succeeds
    mock_k8s_client.create_namespaced_pod.side_effect = ApiException(
        status=500, reason="Internal Server Error"
    )

    # Attempt to start the server
    response: Response = await client.post("servers/test-server-5/start")

    # Should return 500 error
    assert response.status_code == 500
    assert "detail" in response.json()

    # Verify cleanup was attempted (PVC deletion)
    mock_k8s_client.delete_namespaced_persistent_volume_claim.assert_called_once()


async def test_start_server_006_nominal_paper_loader(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock
) -> None:
    """
    Test 006 - Nominal
    Conditions: Paper server (no Modrinth projects)
    Result: HTTP 201 - Pod created without MODRINTH_PROJECTS env vars
    """
    # Add a Paper server without Modrinth projects
    server = Server(
        id="test-server-6", name="Paper Server", loader="paper", game_version="1.20.1"
    )
    test_db.add(server)
    await test_db.commit()

    # Start the server
    response: Response = await client.post("servers/test-server-6/start")

    # Ensure the correct response is returned
    assert response.status_code == 201
    assert "pod" in response.json()

    # Verify Pod was created WITHOUT Modrinth environment variables
    pod_call_args = mock_k8s_client.create_namespaced_pod.call_args
    pod_spec = pod_call_args[0][1]
    env_vars = pod_spec.spec.containers[0].env

    # Check that MODRINTH_PROJECTS is NOT present
    modrinth_projects_env = next((env for env in env_vars if env.name == "MODRINTH_PROJECTS"), None)
    assert modrinth_projects_env is None

    # Check that MODRINTH_DOWNLOAD_DEPENDENCIES is NOT present
    modrinth_deps_env = next(
        (env for env in env_vars if env.name == "MODRINTH_DOWNLOAD_DEPENDENCIES"), None
    )
    assert modrinth_deps_env is None


@pytest.mark.asyncio
async def test_start_server_007_nominal_hostpath_mode(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock, tmp_path
) -> None:
    """
    Test 007 - Nominal
    Conditions: MINECRAFT_HOST_DATA_DIR is set, server uses hostPath instead of PVC
    Result: HTTP 201 - Pod created with hostPath volume, directory created
    """
    import fourdrinier.core.config as config
    import fourdrinier.dependencies.deploy.start_container as start_container_module

    # Set host data dir to temp path
    original_value = config.MINECRAFT_HOST_DATA_DIR
    config.MINECRAFT_HOST_DATA_DIR = str(tmp_path)
    start_container_module.MINECRAFT_HOST_DATA_DIR = str(tmp_path)

    try:
        # Add server
        server = Server(
            id="test-hostpath",
            name="Test Server",
            loader="paper",
            game_version="1.21.1"
        )
        test_db.add(server)
        await test_db.commit()

        # Start the server
        response: Response = await client.post("/servers/test-hostpath/start")

        # Verify response
        assert response.status_code == 201
        assert "pod" in response.json()

        # Verify directory was created
        expected_dir = tmp_path / "Test Server (test-hostpath)"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

        # Verify Pod was created with hostPath volume (not PVC)
        pod_call_args = mock_k8s_client.create_namespaced_pod.call_args
        pod_spec = pod_call_args[0][1]
        volume = pod_spec.spec.volumes[0]
        assert volume.host_path is not None
        assert volume.host_path.path == str(expected_dir)
        assert volume.persistent_volume_claim is None

        # Verify PVC was NOT created in hostPath mode
        mock_k8s_client.create_namespaced_persistent_volume_claim.assert_not_called()

    finally:
        # Restore original config
        config.MINECRAFT_HOST_DATA_DIR = original_value
        start_container_module.MINECRAFT_HOST_DATA_DIR = original_value


@pytest.mark.asyncio
async def test_start_server_008_nominal_hostpath_sanitize_name(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock, tmp_path
) -> None:
    """
    Test 008 - Nominal
    Conditions: hostPath mode with server name containing unsafe filesystem characters
    Result: HTTP 201 - Directory created with sanitized name
    """
    import fourdrinier.core.config as config
    import fourdrinier.dependencies.deploy.start_container as start_container_module

    # Set host data dir to temp path
    original_value = config.MINECRAFT_HOST_DATA_DIR
    config.MINECRAFT_HOST_DATA_DIR = str(tmp_path)
    start_container_module.MINECRAFT_HOST_DATA_DIR = str(tmp_path)

    try:
        # Add server with unsafe characters in name
        server = Server(
            id="test-sanitize",
            name="My/Server:Test*<>?",
            loader="paper",
            game_version="1.21.1"
        )
        test_db.add(server)
        await test_db.commit()

        # Start the server
        response: Response = await client.post("/servers/test-sanitize/start")

        # Verify response
        assert response.status_code == 201
        assert "pod" in response.json()

        # Verify directory was created with sanitized name
        # Expected: "My_Server_Test_____ (test-sanitize)"
        expected_dir = tmp_path / "My_Server_Test_____ (test-sanitize)"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

        # Verify Pod was created with correct hostPath
        pod_call_args = mock_k8s_client.create_namespaced_pod.call_args
        pod_spec = pod_call_args[0][1]
        volume = pod_spec.spec.volumes[0]
        assert volume.host_path is not None
        assert volume.host_path.path == str(expected_dir)

    finally:
        # Restore original config
        config.MINECRAFT_HOST_DATA_DIR = original_value
        start_container_module.MINECRAFT_HOST_DATA_DIR = original_value


@pytest.mark.asyncio
async def test_delete_server_009_hostpath_preserved(
    client: AsyncClient, test_db: AsyncSession, mock_k8s_client: MagicMock, tmp_path
) -> None:
    """
    Test 009 - Nominal
    Conditions: Delete server in hostPath mode
    Result: HTTP 200 - Directory is preserved (not deleted)
    """
    import fourdrinier.core.config as config
    import fourdrinier.dependencies.deploy.start_container as start_container_module

    # Set host data dir to temp path
    original_value = config.MINECRAFT_HOST_DATA_DIR
    config.MINECRAFT_HOST_DATA_DIR = str(tmp_path)
    start_container_module.MINECRAFT_HOST_DATA_DIR = str(tmp_path)

    try:
        # Create server and directory manually
        server = Server(
            id="test-delete",
            name="Delete Test",
            loader="paper",
            game_version="1.21.1"
        )
        test_db.add(server)
        await test_db.commit()

        # Create directory manually to simulate a started server
        server_dir = tmp_path / "Delete Test (test-delete)"
        server_dir.mkdir(parents=True, exist_ok=True)

        # Create a test file in the directory
        test_file = server_dir / "world" / "level.dat"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test data")

        # Verify directory exists before deletion
        assert server_dir.exists()
        assert test_file.exists()

        # Delete the server
        response: Response = await client.delete("/servers/test-delete")

        # Verify response
        assert response.status_code == 200

        # Verify directory is PRESERVED
        assert server_dir.exists()
        assert test_file.exists()
        assert test_file.read_text() == "test data"

        # Verify PVC deletion was NOT attempted (we're in hostPath mode)
        mock_k8s_client.delete_namespaced_persistent_volume_claim.assert_not_called()

    finally:
        # Restore original config
        config.MINECRAFT_HOST_DATA_DIR = original_value
        start_container_module.MINECRAFT_HOST_DATA_DIR = original_value
