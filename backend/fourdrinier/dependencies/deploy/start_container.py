"""
start_container.py

Start a Minecraft server in Kubernetes

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from kubernetes import client
from kubernetes.client.rest import ApiException

from fourdrinier.core.config import MINECRAFT_CPU_LIMIT
from fourdrinier.core.config import MINECRAFT_CPU_REQUEST
from fourdrinier.core.config import MINECRAFT_IMAGE
from fourdrinier.core.config import MINECRAFT_MEMORY_LIMIT
from fourdrinier.core.config import MINECRAFT_MEMORY_REQUEST
from fourdrinier.core.config import MINECRAFT_PVC_SIZE
from fourdrinier.core.config import MINECRAFT_STORAGE_CLASS
from fourdrinier.dependencies.kubernetes_client import get_k8s_client


async def get_server_status(server_id: str) -> str:
    """
    Get the current status of a Minecraft server by checking its Pod status

    Args:
        server_id: Unique server ID

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
            # Check if PVC exists to differentiate between "created" and "stopped"
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
) -> str:
    """
    Start a Minecraft server as a Kubernetes Pod with PVC and LoadBalancer Service

    Args:
        server_name: Human-readable server name (for labels)
        server_id: Unique server ID (used for resource names)
        game_version: Minecraft version to run
        loader: Server loader type (paper, vanilla, forge, fabric)
        modrinth_projects: List of Modrinth project slugs/IDs for mod installation

    Returns:
        Pod name (equivalent to container ID in Docker)

    Raises:
        RuntimeError: If resource creation fails
    """
    v1, namespace = get_k8s_client()

    # Resource names (Kubernetes-compatible: lowercase alphanumeric + hyphens)
    pod_name = f"minecraft-{server_id}"
    pvc_name = f"minecraft-data-{server_id}"
    service_name = f"minecraft-svc-{server_id}"

    try:
        # Step 1: Create PersistentVolumeClaim
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
                resources=client.V1ResourceRequirements(requests={"storage": MINECRAFT_PVC_SIZE}),
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
            client.V1EnvVar(name="VERSION", value=game_version),
            client.V1EnvVar(name="MOTD", value="A Fourdrinier Server"),
        ]

        # Add Fabric + Modrinth configuration if applicable
        if loader == "fabric" and modrinth_projects:
            # Join list into comma-separated string
            projects_str = ",".join(modrinth_projects)
            env_vars.extend([
                client.V1EnvVar(name="MODRINTH_PROJECTS", value=projects_str),
                client.V1EnvVar(name="MODRINTH_DOWNLOAD_DEPENDENCIES", value="required"),
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
                                "cpu": MINECRAFT_CPU_REQUEST,
                                "memory": MINECRAFT_MEMORY_REQUEST,
                            },
                            limits={
                                "cpu": MINECRAFT_CPU_LIMIT,
                                "memory": MINECRAFT_MEMORY_LIMIT,
                            },
                        ),
                        stdin=True,
                        tty=True,
                    )
                ],
                volumes=[
                    client.V1Volume(
                        name="data",
                        persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                            claim_name=pvc_name
                        ),
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
                # Cleanup PVC if pod creation fails
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
                # Cleanup Pod and PVC if service creation fails
                try:
                    v1.delete_namespaced_pod(pod_name, namespace)
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


async def delete_server_resources(server_id: str) -> None:
    """
    Delete all Kubernetes resources for a server (Pod, PVC, Service)

    Args:
        server_id: Unique server ID
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

    # Delete PVC (immediate deletion as per requirements)
    try:
        v1.delete_namespaced_persistent_volume_claim(pvc_name, namespace)
    except ApiException as e:
        if e.status != 404:
            pass
