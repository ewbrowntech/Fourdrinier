"""
start_container.py

Start a Minecraft server in Kubernetes

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

import logging
from pathlib import Path

from fastapi import HTTPException
from kubernetes import client
from kubernetes.client.rest import ApiException
from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.config import MINECRAFT_CPU_LIMIT
from fourdrinier.core.config import MINECRAFT_CPU_REQUEST
from fourdrinier.core.config import MINECRAFT_HOST_DATA_DIR
from fourdrinier.core.config import MINECRAFT_IMAGE
from fourdrinier.core.config import MINECRAFT_MEMORY_LIMIT
from fourdrinier.core.config import MINECRAFT_MEMORY_REQUEST
from fourdrinier.core.config import MINECRAFT_PVC_SIZE
from fourdrinier.core.config import MINECRAFT_STORAGE_CLASS
from fourdrinier.core.utils import sanitize_directory_name
from fourdrinier.dependencies.kubernetes_client import get_k8s_client

logger = logging.getLogger(__name__)


async def get_server_status(server_id: str, server_name: str | None = None) -> str:
    """
    Get the current status of a Minecraft server by checking its Pod status.

    Args:
        server_id: Unique server ID
        server_name: Server name (required for hostPath mode with formatted directories)

    Returns:
        Status string: "running", "pending", "stopped", "created", or "error"
    """
    v1, namespace = get_k8s_client()
    pod_name = f"minecraft-{server_id}"
    pvc_name = f"minecraft-data-{server_id}"

    try:
        pod = v1.read_namespaced_pod(pod_name, namespace)

        # Check pod phase
        phase = pod.status.phase

        if phase == "Running":
            # Check if containers are actually ready
            if pod.status.container_statuses:
                for container_status in pod.status.container_statuses:
                    if not container_status.ready:
                        return "pending"
            return "running"
        elif phase == "Pending":
            return "pending"
        elif phase == "Failed":
            return "error"
        elif phase == "Succeeded":
            return "stopped"
        else:
            return "pending"

    except ApiException as e:
        if e.status == 404:  # Pod not found
            # Check if storage exists to differentiate between "created" and "stopped"
            if MINECRAFT_HOST_DATA_DIR:
                # Check hostPath directory existence
                if server_name:
                    safe_name = sanitize_directory_name(server_name)
                    storage_path = Path(MINECRAFT_HOST_DATA_DIR).resolve() / f"{safe_name} ({server_id})"
                else:
                    # Fallback: use server_id only if name not provided
                    storage_path = Path(MINECRAFT_HOST_DATA_DIR).resolve() / server_id

                if storage_path.exists():
                    return "stopped"
                else:
                    return "created"
            else:
                # Check PVC existence (existing logic)
                try:
                    v1.read_namespaced_persistent_volume_claim(pvc_name, namespace)
                    # PVC exists, so server was started before and is now stopped
                    return "stopped"
                except ApiException as pvc_e:
                    if pvc_e.status == 404:
                        # No PVC, server has never been started
                        return "created"
                    else:
                        return "created"
        else:
            # If we can't determine status, assume created
            return "created"
    except Exception:
        return "created"


async def start_container(
    server_name: str,
    server_id: str,
    game_version: str = "1.20.1",
    loader: str = "paper",
    modrinth_projects: list[str] | None = None,
    db: AsyncSession | None = None,
    # Per-server resource allocation (optional, defaults to global config)
    cpu_request: str | None = None,
    cpu_limit: str | None = None,
    memory_request: str | None = None,
    memory_limit: str | None = None,
    pvc_size: str | None = None,
) -> str:
    """
    Start a Minecraft server as a Kubernetes Pod with PVC and LoadBalancer Service

    Args:
        server_name: Human-readable server name (for labels)
        server_id: Unique server ID (used for resource names)
        game_version: Minecraft version to run
        loader: Server loader type (paper, vanilla, forge, fabric)
        modrinth_projects: List of Modrinth project slugs/IDs for mod installation
        db: Database session for compatibility validation (required for Fabric servers)
        cpu_request: CPU request (e.g., "1000m"), defaults to global config
        cpu_limit: CPU limit (e.g., "2000m"), defaults to global config
        memory_request: Memory request (e.g., "2Gi"), defaults to global config
        memory_limit: Memory limit (e.g., "4Gi"), defaults to global config
        pvc_size: PVC size (e.g., "5Gi"), defaults to global config

    Returns:
        Pod name (equivalent to container ID in Docker)

    Raises:
        RuntimeError: If resource creation fails
        HTTPException: If incompatible mods are detected (400)
    """
    # Use per-server resources or fall back to global config
    final_cpu_request = cpu_request or MINECRAFT_CPU_REQUEST
    final_cpu_limit = cpu_limit or MINECRAFT_CPU_LIMIT
    final_memory_request = memory_request or MINECRAFT_MEMORY_REQUEST
    final_memory_limit = memory_limit or MINECRAFT_MEMORY_LIMIT
    final_pvc_size = pvc_size or MINECRAFT_PVC_SIZE
    # CRITICAL: Validate modrinth projects compatibility BEFORE creating any resources
    if loader == "fabric" and modrinth_projects and db:
        from fourdrinier.db.models import Server
        from fourdrinier.services.compatibility_validator import validate_server_modrinth_projects

        # Create temporary server object for validation
        temp_server = Server(
            id=server_id,
            name=server_name,
            loader=loader,
            game_version=game_version,
            modrinth_projects=modrinth_projects,
        )

        validation_result = await validate_server_modrinth_projects(temp_server, db)

        if not validation_result["compatible"]:
            # BLOCK startup - incompatible mods will crash the server
            incompatible_count = len(validation_result["incompatible_projects"])
            error_details = "\n".join(validation_result["warnings"])

            logger.error(
                f"Server {server_id} startup blocked: {incompatible_count} incompatible mod(s) detected. "
                f"Details: {error_details}"
            )

            raise HTTPException(
                status_code=400,
                detail=f"Cannot start server with {incompatible_count} incompatible mod(s):\n{error_details}"
            )

    v1, namespace = get_k8s_client()

    # Resource names (Kubernetes-compatible: lowercase alphanumeric + hyphens)
    pod_name = f"minecraft-{server_id}"
    pvc_name = f"minecraft-data-{server_id}"
    service_name = f"minecraft-svc-{server_id}"

    try:
        # Step 1: Create storage (PVC or hostPath directory)
        if MINECRAFT_HOST_DATA_DIR:
            # hostPath mode: Create directory on host
            safe_name = sanitize_directory_name(server_name)
            server_dir = Path(MINECRAFT_HOST_DATA_DIR).resolve() / f"{safe_name} ({server_id})"
            try:
                server_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created/verified host directory: {server_dir}")
            except OSError as e:
                raise RuntimeError(f"Failed to create host directory {server_dir}: {e}")
        else:
            # PVC mode: Create PersistentVolumeClaim (existing logic)
            pvc = client.V1PersistentVolumeClaim(
                metadata=client.V1ObjectMeta(
                    name=pvc_name,
                    labels={
                        "app": "fourdrinier",
                        "component": "minecraft-server",
                        "server-id": server_id,
                    },
                ),
                spec=client.V1PersistentVolumeClaimSpec(
                    access_modes=["ReadWriteOnce"],
                    storage_class_name=MINECRAFT_STORAGE_CLASS,
                    resources=client.V1ResourceRequirements(requests={"storage": final_pvc_size}),
                ),
            )

            try:
                v1.create_namespaced_persistent_volume_claim(namespace, pvc)
            except ApiException as e:
                if e.status == 409:  # Already exists
                    pass  # Idempotent: PVC already exists
                else:
                    raise RuntimeError(f"Failed to create PVC: {e}")

        # Step 2: Create Pod
        # Build environment variables dynamically
        env_vars = [
            client.V1EnvVar(name="EULA", value="true"),
            client.V1EnvVar(name="TYPE", value=loader.upper()),
            client.V1EnvVar(name="VERSION", value=game_version),
            client.V1EnvVar(name="MOTD", value="A Fourdrinier Server"),
        ]

        # Set JVM memory using INIT_MEMORY and MAX_MEMORY for separate control
        # The Minecraft Docker image supports these for -Xms and -Xmx respectively
        if final_memory_request:
            # Convert Kubernetes format (e.g., "8Gi") to Docker image format (e.g., "8G")
            init_memory = final_memory_request.replace("i", "")  # 8Gi -> 8G
            env_vars.append(client.V1EnvVar(name="INIT_MEMORY", value=init_memory))

        if final_memory_limit:
            # Convert Kubernetes format (e.g., "16Gi") to Docker image format (e.g., "16G")
            max_memory = final_memory_limit.replace("i", "")  # 16Gi -> 16G
            env_vars.append(client.V1EnvVar(name="MAX_MEMORY", value=max_memory))

        # Add Fabric + Modrinth configuration if applicable
        if loader == "fabric" and modrinth_projects:
            # Join list into comma-separated string
            projects_str = ",".join(modrinth_projects)
            env_vars.extend([
                client.V1EnvVar(name="MODRINTH_PROJECTS", value=projects_str),
                client.V1EnvVar(name="MODRINTH_DOWNLOAD_DEPENDENCIES", value="required"),
                client.V1EnvVar(name="MODRINTH_ALLOWED_VERSION_TYPE", value="alpha"),
            ])

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                labels={
                    "app": "fourdrinier",
                    "component": "minecraft-server",
                    "server-id": server_id,
                },
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="minecraft",
                        image=MINECRAFT_IMAGE,
                        ports=[client.V1ContainerPort(container_port=25565, protocol="TCP")],
                        env=env_vars,
                        volume_mounts=[client.V1VolumeMount(name="data", mount_path="/data")],
                        resources=client.V1ResourceRequirements(
                            requests={
                                "cpu": final_cpu_request,
                                "memory": final_memory_request,
                            },
                            limits={
                                "cpu": final_cpu_limit,
                                "memory": final_memory_limit,
                            },
                        ),
                        stdin=True,
                        tty=True,
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="data",
                        host_path=client.V1HostPathVolumeSource(
                            path=str(Path(MINECRAFT_HOST_DATA_DIR).resolve() / f"{sanitize_directory_name(server_name)} ({server_id})"),
                            type="DirectoryOrCreate",
                        ) if MINECRAFT_HOST_DATA_DIR else None,
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        ) if not MINECRAFT_HOST_DATA_DIR else None,
                    )
                ],
                restart_policy="Always",
            ),
        )

        try:
            v1.create_namespaced_pod(namespace, pod)
        except ApiException as e:
            if e.status == 409:  # Already exists
                pass  # Idempotent: Pod already exists
            else:
                # Cleanup on pod creation failure
                # Note: In hostPath mode, preserve directory even on failure
                # In PVC mode, clean up PVC
                if not MINECRAFT_HOST_DATA_DIR:
                    try:
                        v1.delete_namespaced_persistent_volume_claim(pvc_name, namespace)
                    except Exception:
                        pass
                raise RuntimeError(f"Failed to create Pod: {e}")

        # Step 3: Create LoadBalancer Service
        service = client.V1Service(
            metadata=client.V1ObjectMeta(
                name=service_name,
                labels={
                    "app": "fourdrinier",
                    "component": "minecraft-server",
                    "server-id": server_id,
                },
            ),
            spec=client.V1ServiceSpec(
                type="LoadBalancer",
                selector={
                    "server-id": server_id,
                },
                ports=[
                    client.V1ServicePort(
                        name="minecraft",
                        port=25565,
                        target_port=25565,
                        protocol="TCP",
                    )
                ],
            ),
        )

        try:
            v1.create_namespaced_service(namespace, service)
        except ApiException as e:
            if e.status == 409:  # Already exists
                pass  # Idempotent: Service already exists
            else:
                # Cleanup Pod and PVC/directory if service creation fails
                try:
                    v1.delete_namespaced_pod(pod_name, namespace)
                    if not MINECRAFT_HOST_DATA_DIR:
                        v1.delete_namespaced_persistent_volume_claim(pvc_name, namespace)
                except Exception:
                    pass
                raise RuntimeError(f"Failed to create Service: {e}")

        return pod_name

    except Exception as e:
        raise RuntimeError(f"Failed to start Minecraft server: {str(e)}")


async def stop_container(server_id: str) -> None:
    """
    Stop a Minecraft server by deleting its Pod

    Note: PVC and Service are NOT deleted (allows restart with data intact)
    This function returns immediately and the deletion happens in the background.

    Args:
        server_id: Unique server ID
    """
    import asyncio

    v1, namespace = get_k8s_client()
    pod_name = f"minecraft-{server_id}"

    def _delete_pod():
        try:
            v1.delete_namespaced_pod(
                pod_name,
                namespace,
                grace_period_seconds=0,  # Immediate deletion to avoid hanging with active log streams
                propagation_policy="Background",  # Delete asynchronously without blocking
                _request_timeout=5.0,  # Force client-side timeout to prevent hanging
            )
        except ApiException as e:
            if e.status == 404:  # Not found
                pass  # Idempotent: already stopped
            else:
                # Log error but don't raise since this is fire-and-forget
                import logging
                logging.error(f"Failed to stop Pod {pod_name}: {e}")
        except Exception as e:
            # Handle timeout or other exceptions
            import logging
            logging.error(f"Error deleting Pod {pod_name}: {e}")

    # Fire and forget - run in background without waiting
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _delete_pod)
    # Return immediately without awaiting


async def stream_server_logs(server_id: str, tail_lines: int = 100):
    """
    Stream logs from a Minecraft server pod in real-time

    Args:
        server_id: Unique server ID
        tail_lines: Number of log lines to retrieve initially from the end (default: 100)

    Yields:
        Log lines as Server-Sent Events (SSE)

    Raises:
        RuntimeError: If pod not found or logs cannot be retrieved
    """
    import asyncio
    import threading

    v1, namespace = get_k8s_client()
    pod_name = f"minecraft-{server_id}"

    try:
        # Poll until container is ready or timeout
        max_wait_time = 300  # 5 minutes
        poll_interval = 2  # 2 seconds
        elapsed_time = 0

        while elapsed_time < max_wait_time:
            try:
                pod = v1.read_namespaced_pod(pod_name, namespace)

                # Check if container is ready
                container_ready = False
                if pod.status.container_statuses:
                    container_status = pod.status.container_statuses[0]
                    if container_status.state.running:
                        container_ready = True
                    elif container_status.state.waiting:
                        # Send status update
                        reason = container_status.state.waiting.reason or "Starting"
                        yield f"data: Container is {reason.lower()}. Waiting for logs...\n\n"
                    elif container_status.state.terminated:
                        # Container has been stopped
                        yield f"data: Container has been stopped.\n\n"
                        return
                else:
                    # No container statuses yet - pod is still initializing
                    yield f"data: Pod initializing...\n\n"

                if container_ready:
                    break

                # Wait before next poll
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval

            except ApiException as e:
                if e.status == 404:
                    raise RuntimeError("Server pod not found. Server may not be running.")
                else:
                    # Temporary error, keep trying
                    yield f"data: Waiting for container...\n\n"
                    await asyncio.sleep(poll_interval)
                    elapsed_time += poll_interval

        # If we timed out waiting for container
        if elapsed_time >= max_wait_time:
            yield f"data: Timeout waiting for container to start\n\n"
            return

        # Container is ready, stream logs
        stream = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            follow=True,
            tail_lines=tail_lines,
            timestamps=True,
            _preload_content=False,  # Required for streaming
        )

        # Move the blocking log stream off the event loop so other requests (like stop)
        # are still served while logs are being tailed.
        loop = asyncio.get_running_loop()
        log_queue: asyncio.Queue[object] = asyncio.Queue()
        stop_event = threading.Event()

        def _pump_logs() -> None:
            try:
                for line in stream:
                    if stop_event.is_set():
                        break
                    if not line:
                        continue
                    decoded_line = line.decode("utf-8") if isinstance(line, bytes) else line
                    loop.call_soon_threadsafe(log_queue.put_nowait, decoded_line)
            except Exception as exc:  # Surface errors back to the coroutine
                loop.call_soon_threadsafe(log_queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(log_queue.put_nowait, None)
                try:
                    stream.close()
                except Exception:
                    pass

        worker = loop.run_in_executor(None, _pump_logs)

        try:
            while True:
                item = await log_queue.get()
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                # Format as SSE: each message must be prefixed with "data: " and end with \n\n
                yield f"data: {item}\n\n"
        finally:
            stop_event.set()
            # Give the background thread a moment to exit; ignore timeouts.
            try:
                await asyncio.wait_for(worker, timeout=2)
            except Exception:
                pass

    except ApiException as e:
        if e.status == 404:
            raise RuntimeError("Server pod not found. Server may not be running.")
        elif e.status == 400:
            # Container not ready yet - format as SSE
            yield "data: Container is starting. Waiting for logs...\n\n"
        else:
            raise RuntimeError(f"Failed to retrieve logs: {e}")


async def delete_server_resources(server_id: str, server_name: str | None = None) -> None:
    """
    Delete all Kubernetes resources for a server (Pod, PVC, Service).

    Note: In hostPath mode, directories are PRESERVED (not deleted).

    Args:
        server_id: Unique server ID
        server_name: Server name (for logging in hostPath mode)
    """
    v1, namespace = get_k8s_client()

    pod_name = f"minecraft-{server_id}"
    pvc_name = f"minecraft-data-{server_id}"
    service_name = f"minecraft-svc-{server_id}"

    # Delete Pod (with immediate grace period)
    try:
        v1.delete_namespaced_pod(pod_name, namespace, grace_period_seconds=0)  # Immediate deletion
    except ApiException as e:
        if e.status != 404:  # Ignore not found
            # Log but don't fail - continue cleanup
            pass

    # Delete Service
    try:
        v1.delete_namespaced_service(service_name, namespace)
    except ApiException as e:
        if e.status != 404:
            pass

    # Delete storage (PVC only - hostPath directories are preserved)
    if MINECRAFT_HOST_DATA_DIR:
        # Log preservation message
        if server_name:
            safe_name = sanitize_directory_name(server_name)
            server_dir = Path(MINECRAFT_HOST_DATA_DIR).resolve() / f"{safe_name} ({server_id})"
        else:
            server_dir = Path(MINECRAFT_HOST_DATA_DIR).resolve() / server_id
        logger.info(f"Server deleted - directory preserved at: {server_dir}")
    else:
        # Delete PVC (immediate deletion as per requirements)
        try:
            v1.delete_namespaced_persistent_volume_claim(pvc_name, namespace)
        except ApiException as e:
            if e.status != 404:
                pass
