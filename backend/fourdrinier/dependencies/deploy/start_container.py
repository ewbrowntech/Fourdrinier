"""
start_container.py

Start a Minecraft server in Kubernetes

Copyright (C) 2024 by Ethan Brown
All rights reserved. This file is part of the Fourdrinier project and is released under
the GPLv3 License. See the LICENSE file for more details.
"""

from kubernetes import client
from kubernetes.client.rest import ApiException

from fourdrinier.core.config import (
    MINECRAFT_CPU_LIMIT,
    MINECRAFT_CPU_REQUEST,
    MINECRAFT_IMAGE,
    MINECRAFT_MEMORY_LIMIT,
    MINECRAFT_MEMORY_REQUEST,
    MINECRAFT_PVC_SIZE,
    MINECRAFT_STORAGE_CLASS,
)
from fourdrinier.dependencies.kubernetes_client import get_k8s_client


async def start_container(
    server_name: str, server_id: str, game_version: str = "1.20.1"
) -> str:
    """
    Start a Minecraft server as a Kubernetes Pod with PVC and LoadBalancer Service

    Args:
        server_name: Human-readable server name (for labels)
        server_id: Unique server ID (used for resource names)
        game_version: Minecraft version to run

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
                resources=client.V1ResourceRequirements(
                    requests={"storage": MINECRAFT_PVC_SIZE}
                ),
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
                        env=[
                            client.V1EnvVar(name="EULA", value="true"),
                            client.V1EnvVar(name="VERSION", value=game_version),
                            client.V1EnvVar(name="MOTD", value="A Fourdrinier Server"),
                        ],
                        volume_mounts=[
                            client.V1VolumeMount(name="data", mount_path="/data")
                        ],
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

    Args:
        server_id: Unique server ID
    """
    v1, namespace = get_k8s_client()
    pod_name = f"minecraft-{server_id}"

    try:
        v1.delete_namespaced_pod(
            pod_name, namespace, grace_period_seconds=30  # Allow graceful shutdown
        )
    except ApiException as e:
        if e.status == 404:  # Not found
            return  # Idempotent: already stopped
        else:
            raise RuntimeError(f"Failed to stop Pod: {e}")


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
        v1.delete_namespaced_pod(
            pod_name, namespace, grace_period_seconds=0  # Immediate deletion
        )
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
