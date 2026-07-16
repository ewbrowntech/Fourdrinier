"""
support.py

Provide shared test data and dependency doubles for HostService unit tests.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast
from unittest.mock import AsyncMock, Mock

from sqlalchemy.ext.asyncio import AsyncSession

from fourdrinier.core.secrets import SecretEncryptor
from fourdrinier.db.models import Host
from fourdrinier.hosts import HostType
from fourdrinier.hosts.docker.types import DockerHostPingResult, ObservedHostKey
from fourdrinier.hosts.drivers import HostDriverRegistry
from fourdrinier.hosts.service import HostService
from fourdrinier.schemas.host import DockerHostCreate, KubernetesHostCreate
from tests.test_api.test_hosts.support import CA_PEM

HOST_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000101")
KEYPAIR_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000103")
OBSERVED_AT: datetime = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)


@dataclass(slots=True)
class CrudMocks:
    """Collect CRUD test doubles used by HostService tests."""

    create_host: AsyncMock
    delete_host: AsyncMock
    get_host: AsyncMock
    get_keypair: AsyncMock
    list_hosts: AsyncMock


def service_dependencies() -> tuple[HostService, AsyncMock, Mock, Mock]:
    """Build an isolated HostService and its direct dependencies.

    Returns:
        The service, session, driver registry, and secret encryptor test doubles.
    """
    session: AsyncMock = AsyncMock(spec=AsyncSession)
    drivers: Mock = Mock(spec=HostDriverRegistry)
    secret_encryptor: Mock = Mock(spec=SecretEncryptor)
    service: HostService = HostService(
        session=cast(AsyncSession, session),
        drivers=cast(HostDriverRegistry, drivers),
        secret_encryptor=cast(SecretEncryptor, secret_encryptor),
    )
    return service, session, drivers, secret_encryptor


def docker_request() -> DockerHostCreate:
    """Build a valid Docker host creation request.

    Returns:
        A Docker host creation request with stable test values.
    """
    request: DockerHostCreate = DockerHostCreate(
        type="docker",
        name="docker-production",
        enabled=False,
        labels={"environment": "production"},
        address="203.0.113.10",
        port=2222,
        username="docker",
        keypair_id=KEYPAIR_ID,
    )
    return request


def kubernetes_request() -> KubernetesHostCreate:
    """Build a valid Kubernetes host creation request.

    Returns:
        A Kubernetes host creation request with stable test values.
    """
    request: KubernetesHostCreate = KubernetesHostCreate(
        type="kubernetes",
        name="kubernetes-production",
        enabled=True,
        labels={"environment": "production"},
        api_url="https://203.0.113.20:6443",
        ca_cert_pem=CA_PEM,
        token="service-account-token",
        namespace="fourdrinier",
    )
    return request


def host(host_type: HostType = HostType.DOCKER) -> Host:
    """Build a persisted host aggregate.

    Args:
        host_type: Provider type assigned to the host.

    Returns:
        A host aggregate with a stable identifier.
    """
    persisted: Host = Host(id=HOST_ID, type=host_type, name="production")
    return persisted


def ping_result() -> DockerHostPingResult:
    """Build a successful Docker host ping result.

    Returns:
        Provider observations with stable test values.
    """
    result: DockerHostPingResult = DockerHostPingResult(
        host_id=HOST_ID,
        type=HostType.DOCKER,
        latency_ms=2.5,
        observed_at=OBSERVED_AT,
        docker_version="27.0.1",
        api_version="1.47",
        os="linux",
        arch="amd64",
        host_key=ObservedHostKey(
            key_type="ssh-ed25519",
            key_b64="AAAA test",
            fingerprint="SHA256:test",
            first_seen=True,
        ),
    )
    return result
