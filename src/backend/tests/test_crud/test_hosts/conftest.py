"""
conftest.py

Provide host aggregate factories for host CRUD tests.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from fourdrinier.db.models import (
    DockerHostDetails,
    Host,
    KeypairSource,
    KubernetesHostDetails,
    SSHKeypair,
)
from fourdrinier.hosts.types import HostType


@pytest.fixture
def docker_host_factory() -> Callable[[str], Host]:
    """Build Docker host aggregates with their SSH keypairs.

    Returns:
        A factory that builds a Docker host aggregate with the supplied name.
    """

    def build_docker_host(name: str) -> Host:
        keypair: SSHKeypair = SSHKeypair(
            name=f"{name}-key",
            source=KeypairSource.GENERATED,
            algorithm="ed25519",
            public_key=f"ssh-ed25519 AAAA {name}",
            fingerprint=f"SHA256:{name}",
            private_key_encrypted=b"encrypted",
        )
        host: Host = Host(
            type=HostType.DOCKER,
            name=name,
            labels={"provider": "docker"},
            docker_details=DockerHostDetails(
                address="203.0.113.10",
                port=22,
                username="docker",
                keypair=keypair,
            ),
        )
        return host

    return build_docker_host


@pytest.fixture
def kubernetes_host_factory() -> Callable[[str], Host]:
    """Build Kubernetes host aggregates.

    Returns:
        A factory that builds a Kubernetes host aggregate with the supplied name.
    """

    def build_kubernetes_host(name: str) -> Host:
        host: Host = Host(
            type=HostType.KUBERNETES,
            name=name,
            labels={"provider": "kubernetes"},
            kubernetes_details=KubernetesHostDetails(
                api_url="https://203.0.113.20:6443",
                ca_cert_pem="certificate",
                token_encrypted=b"encrypted-token",
                namespace="fourdrinier",
            ),
        )
        return host

    return build_kubernetes_host
