"""
test_kubernetes_driver.py

Unit tests for KubernetesHostDriver.ping.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest

from fourdrinier.core.secrets import EncryptedSecret, PlaintextSecret, SecretDecryptor
from fourdrinier.db.models import Host, KubernetesHostDetails
from fourdrinier.hosts import (
    HostAuthenticationError,
    HostPermissionDeniedError,
    HostProviderMismatchError,
    HostTrustVerificationError,
    HostType,
    HostUnreachableError,
)
from fourdrinier.hosts.kubernetes import (
    KubernetesHostDriver,
    KubernetesHostPingResult,
)
from fourdrinier.hosts.kubernetes.errors import (
    ClusterUnreachableError,
    KubernetesAuthError,
    KubernetesRBACError,
    TLSVerificationError,
)
from fourdrinier.hosts.kubernetes.operations import ping as kubernetes_ping
from fourdrinier.hosts.kubernetes.operations.ping import KubernetesPingObservation

_HOST_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000201")


def _kubernetes_host(*, token_encrypted: bytes = b"ciphertext") -> Host:
    host: Host = Host(
        id=_HOST_ID,
        type=HostType.KUBERNETES,
        name="production",
        kubernetes_details=KubernetesHostDetails(
            api_url="https://203.0.113.20:6443",
            ca_cert_pem="certificate",
            token_encrypted=token_encrypted,
            namespace="fourdrinier",
        ),
    )
    return host


async def test_kubernetes_host_driver_ping_001_anomalous_host_type_does_not_match() -> None:
    """Test 001 - Anomalous
    Condition: The Kubernetes driver receives a Docker host
    Result: HostProviderMismatchError is raised before any remote operation
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    driver: KubernetesHostDriver = KubernetesHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = Host(type=HostType.DOCKER, name="production")

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="the Kubernetes driver cannot operate on a docker host",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.KUBERNETES
    decryptor.decrypt.assert_not_called()


async def test_kubernetes_host_driver_ping_002_nominal_cluster_is_observed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test 002 - Nominal
    Condition: Stored credentials decrypt and the cluster accepts all ping checks
    Result: Provider-neutral and Kubernetes observations are returned with an aware timestamp
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"service-account-token")
    remote_result: KubernetesPingObservation = KubernetesPingObservation(
        latency_ms=8.7,
        git_version="v1.31.4+k3s1",
        platform="linux/amd64",
        username="system:serviceaccount:fourdrinier:fourdrinier",
        namespace="fourdrinier",
    )
    ping_cluster: AsyncMock = AsyncMock(
        spec=kubernetes_ping._ping_remote,
        return_value=remote_result,
    )
    monkeypatch.setattr(kubernetes_ping, "_ping_remote", ping_cluster)
    driver: KubernetesHostDriver = KubernetesHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _kubernetes_host()

    # Act
    result: KubernetesHostPingResult = await driver.ping(host)

    # Assert
    assert result.host_id == _HOST_ID
    assert result.type is HostType.KUBERNETES
    assert result.latency_ms == 8.7
    assert result.observed_at.tzinfo is UTC
    assert result.git_version == remote_result.git_version
    assert result.platform == remote_result.platform
    assert result.username == remote_result.username
    assert result.namespace == remote_result.namespace
    decryptor.decrypt.assert_called_once_with(EncryptedSecret(b"ciphertext"))
    ping_cluster.assert_awaited_once_with(
        api_url="https://203.0.113.20:6443",
        token="service-account-token",
        ca_cert_pem="certificate",
        namespace="fourdrinier",
    )


async def test_kubernetes_host_driver_ping_003_anomalous_details_are_missing() -> None:
    """Test 003 - Anomalous
    Condition: A Kubernetes host aggregate has no Kubernetes details loaded
    Result: HostProviderMismatchError identifies the malformed Kubernetes aggregate
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    driver: KubernetesHostDriver = KubernetesHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = Host(id=_HOST_ID, type=HostType.KUBERNETES, name="production")

    # Act
    with pytest.raises(
        HostProviderMismatchError,
        match="the Kubernetes host has no Kubernetes details",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.KUBERNETES
    decryptor.decrypt.assert_not_called()


async def test_kubernetes_host_driver_ping_004_anomalous_token_is_not_utf8() -> None:
    """Test 004 - Anomalous
    Condition: The decrypted bearer token is not valid UTF-8
    Result: HostAuthenticationError is raised before contacting the cluster
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"\xff")
    driver: KubernetesHostDriver = KubernetesHostDriver(cast(SecretDecryptor, decryptor))
    host: Host = _kubernetes_host()

    # Act
    with pytest.raises(
        HostAuthenticationError,
        match="the stored Kubernetes bearer token is not valid UTF-8",
    ) as captured:
        await driver.ping(host)

    # Assert
    assert captured.value.provider is HostType.KUBERNETES
    assert isinstance(captured.value.__cause__, UnicodeDecodeError)


@pytest.mark.parametrize(
    ("provider_error", "domain_error"),
    [
        pytest.param(
            KubernetesAuthError("token rejected"),
            HostAuthenticationError,
            id="authentication",
        ),
        pytest.param(
            KubernetesRBACError("not allowed"),
            HostPermissionDeniedError,
            id="permission",
        ),
        pytest.param(
            TLSVerificationError("untrusted certificate"),
            HostTrustVerificationError,
            id="trust",
        ),
        pytest.param(
            ClusterUnreachableError("no route"),
            HostUnreachableError,
            id="unreachable",
        ),
    ],
)
async def test_kubernetes_host_driver_ping_005_anomalous_provider_failure_is_translated(
    monkeypatch: pytest.MonkeyPatch,
    provider_error: Exception,
    domain_error: type[Exception],
) -> None:
    """Test 005 - Anomalous
    Condition: The Kubernetes ping boundary reports a typed provider failure
    Result: The matching stable host-domain error preserves the message and cause
    """
    # Arrange
    decryptor: Mock = Mock(spec=SecretDecryptor)
    decryptor.decrypt.return_value = PlaintextSecret(b"service-account-token")
    ping_cluster: AsyncMock = AsyncMock(
        spec=kubernetes_ping._ping_remote,
        side_effect=provider_error,
    )
    monkeypatch.setattr(kubernetes_ping, "_ping_remote", ping_cluster)
    driver: KubernetesHostDriver = KubernetesHostDriver(cast(SecretDecryptor, decryptor))

    # Act
    with pytest.raises(domain_error, match=str(provider_error)) as captured:
        await driver.ping(_kubernetes_host())

    # Assert
    assert captured.value.__cause__ is provider_error
    assert captured.value.provider is HostType.KUBERNETES
