"""
test_host.py

Unit tests for host Pydantic contracts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID
from pydantic import TypeAdapter, ValidationError

from fourdrinier.schemas.host import (
    DockerHostCreate,
    DockerHostRead,
    DockerHostUpdate,
    DockerPingResponse,
    HostCreate,
    HostListResponse,
    HostPingResponse,
    HostRead,
    HostUpdate,
    KubernetesHostCreate,
    KubernetesHostRead,
    KubernetesHostUpdate,
    KubernetesPingResponse,
)

_KEYPAIR_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_HOST_ID: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_TIMESTAMP: datetime = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)


def _make_ca_pem() -> str:
    key: ed25519.Ed25519PrivateKey = ed25519.Ed25519PrivateKey.generate()
    subject: x509.Name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
    certificate: x509.Certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(_TIMESTAMP)
        .not_valid_after(_TIMESTAMP + timedelta(days=1))
        .sign(key, algorithm=None)
    )
    return certificate.public_bytes(Encoding.PEM).decode()


_CA_PEM: str = _make_ca_pem()


def _docker_create_payload() -> dict[str, Any]:
    return {
        "type": "docker",
        "name": "docker-production",
        "address": "203.0.113.10",
        "username": "docker",
        "keypair_id": str(_KEYPAIR_ID),
    }


def _kubernetes_create_payload() -> dict[str, Any]:
    return {
        "type": "kubernetes",
        "name": "kubernetes-production",
        "api_url": "https://203.0.113.20:6443",
        "ca_cert_pem": _CA_PEM,
        "token": "service-account-token",
    }


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        pytest.param(_docker_create_payload(), DockerHostCreate, id="docker"),
        pytest.param(_kubernetes_create_payload(), KubernetesHostCreate, id="kubernetes"),
    ],
)
def test_host_create_001_nominal_provider_payload_is_selected_by_type(
    payload: dict[str, Any],
    expected_type: type[DockerHostCreate] | type[KubernetesHostCreate],
) -> None:
    """Test 001 - Nominal
    Condition: A complete payload has a known Docker or Kubernetes type
    Result: The discriminator selects and validates the matching provider schema
    """
    # Arrange
    adapter: TypeAdapter[HostCreate] = TypeAdapter(HostCreate)

    # Act
    result: DockerHostCreate | KubernetesHostCreate = adapter.validate_python(payload)

    # Assert
    assert isinstance(result, expected_type)
    assert result.enabled is True
    assert result.labels == {}


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(
            {
                **_docker_create_payload(),
                "api_url": "https://203.0.113.20:6443",
                "ca_cert_pem": _CA_PEM,
                "token": "service-account-token",
            },
            id="kubernetes-fields-on-docker",
        ),
        pytest.param(
            {
                **_kubernetes_create_payload(),
                "address": "203.0.113.10",
                "username": "docker",
                "keypair_id": str(_KEYPAIR_ID),
            },
            id="docker-fields-on-kubernetes",
        ),
    ],
)
def test_host_create_002_anomalous_wrong_provider_fields_are_rejected(
    payload: dict[str, Any],
) -> None:
    """Test 002 - Anomalous
    Condition: A valid provider payload also contains fields owned by the other provider
    Result: ValidationError reports that extra inputs are not permitted
    """
    # Arrange
    adapter: TypeAdapter[HostCreate] = TypeAdapter(HostCreate)

    # Act / Assert
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        adapter.validate_python(payload)


@pytest.mark.parametrize(
    ("type_value", "message"),
    [
        pytest.param(None, "Unable to extract tag", id="missing"),
        pytest.param("nomad", "does not match any of the expected tags", id="unknown"),
    ],
)
def test_host_create_003_anomalous_missing_or_unknown_type_is_rejected(
    type_value: str | None,
    message: str,
) -> None:
    """Test 003 - Anomalous
    Condition: A create payload omits type or supplies an unsupported provider type
    Result: ValidationError reports a missing or invalid discriminator tag
    """
    # Arrange
    payload: dict[str, Any] = _docker_create_payload()
    if type_value is None:
        del payload["type"]
    else:
        payload["type"] = type_value
    adapter: TypeAdapter[HostCreate] = TypeAdapter(HostCreate)

    # Act / Assert
    with pytest.raises(ValidationError, match=message):
        adapter.validate_python(payload)


@pytest.mark.parametrize(
    ("payload", "missing_field"),
    [
        pytest.param(
            {key: value for key, value in _docker_create_payload().items() if key != "address"},
            "address",
            id="docker-address",
        ),
        pytest.param(
            {key: value for key, value in _kubernetes_create_payload().items() if key != "token"},
            "token",
            id="kubernetes-token",
        ),
    ],
)
def test_host_create_004_anomalous_required_provider_field_is_missing(
    payload: dict[str, Any],
    missing_field: str,
) -> None:
    """Test 004 - Anomalous
    Condition: A provider payload omits one field required by its selected schema
    Result: ValidationError identifies the missing provider field
    """
    # Arrange
    adapter: TypeAdapter[HostCreate] = TypeAdapter(HostCreate)

    # Act / Assert
    with pytest.raises(ValidationError, match=missing_field):
        adapter.validate_python(payload)


def test_host_create_005_anomalous_unknown_extra_field_is_rejected() -> None:
    """Test 005 - Anomalous
    Condition: A complete create payload contains a field outside the host contract
    Result: ValidationError reports that the extra input is not permitted
    """
    # Arrange
    payload: dict[str, Any] = {**_docker_create_payload(), "ssh_password": "secret"}
    adapter: TypeAdapter[HostCreate] = TypeAdapter(HostCreate)

    # Act / Assert
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        adapter.validate_python(payload)


def test_kubernetes_host_create_006_anomalous_invalid_certificate_bundle_is_rejected() -> None:
    """Test 006 - Anomalous
    Condition: A Kubernetes create payload contains invalid certificate material
    Result: ValidationError reports that the value is not a PEM certificate bundle
    """
    # Arrange
    payload: dict[str, Any] = {
        **_kubernetes_create_payload(),
        "ca_cert_pem": "not a certificate",
    }

    # Act / Assert
    with pytest.raises(ValidationError, match="not a valid PEM certificate bundle"):
        KubernetesHostCreate.model_validate(payload)


def test_host_read_007_nominal_kubernetes_secrets_are_omitted() -> None:
    """Test 007 - Nominal
    Condition: A Kubernetes persistence object includes credentials and CA trust material
    Result: The read response contains public fields and omits all secret or bulky material
    """
    # Arrange
    source: SimpleNamespace = SimpleNamespace(
        id=_HOST_ID,
        type="kubernetes",
        name="kubernetes-production",
        api_url="https://203.0.113.20:6443",
        namespace="fourdrinier",
        enabled=True,
        labels={"environment": "production"},
        last_seen_at=None,
        created_at=_TIMESTAMP,
        updated_at=_TIMESTAMP,
        ca_cert_pem=_CA_PEM,
        token="service-account-token",
        token_encrypted=b"encrypted-service-account-token",
    )
    adapter: TypeAdapter[HostRead] = TypeAdapter(HostRead)

    # Act
    result: DockerHostRead | KubernetesHostRead = adapter.validate_python(source)
    response: dict[str, Any] = result.model_dump(mode="json")

    # Assert
    assert isinstance(result, KubernetesHostRead)
    assert response["api_url"] == "https://203.0.113.20:6443"
    assert "ca_cert_pem" not in response
    assert "token" not in response
    assert "token_encrypted" not in response


def test_host_list_response_008_nominal_mixed_provider_list_is_validated() -> None:
    """Test 008 - Nominal
    Condition: A host list contains complete Docker and Kubernetes read payloads
    Result: Each item is validated against the schema selected by its type
    """
    # Arrange
    common: dict[str, Any] = {
        "enabled": True,
        "labels": {},
        "last_seen_at": None,
        "created_at": _TIMESTAMP,
        "updated_at": _TIMESTAMP,
    }
    payload: list[dict[str, Any]] = [
        {
            **common,
            "id": _HOST_ID,
            "type": "docker",
            "name": "docker-production",
            "address": "203.0.113.10",
            "port": 22,
            "username": "docker",
            "keypair_id": _KEYPAIR_ID,
            "host_key_fingerprint": None,
        },
        {
            **common,
            "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
            "type": "kubernetes",
            "name": "kubernetes-production",
            "api_url": "https://203.0.113.20:6443",
            "namespace": "fourdrinier",
        },
    ]
    adapter: TypeAdapter[HostListResponse] = TypeAdapter(HostListResponse)

    # Act
    result: HostListResponse = adapter.validate_python(payload)

    # Assert
    assert isinstance(result[0], DockerHostRead)
    assert isinstance(result[1], KubernetesHostRead)


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        pytest.param(
            {
                "type": "docker",
                "latency_ms": 2.5,
                "docker_version": "27.0.1",
                "api_version": "1.47",
                "os": "linux",
                "arch": "amd64",
                "host_key": {
                    "fingerprint": "SHA256:test",
                    "key_type": "ssh-ed25519",
                    "first_seen": True,
                },
            },
            "docker",
            id="docker",
        ),
        pytest.param(
            {
                "type": "kubernetes",
                "latency_ms": 3.5,
                "git_version": "v1.31.4",
                "platform": "linux/amd64",
                "username": "system:serviceaccount:fourdrinier:fourdrinier",
                "namespace": "fourdrinier",
            },
            "kubernetes",
            id="kubernetes",
        ),
    ],
)
def test_ping_response_009_nominal_provider_payload_is_selected_by_type(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    """Test 009 - Nominal
    Condition: A successful ping payload has a supported provider type
    Result: The discriminator selects the matching response and supplies success defaults
    """
    # Arrange
    adapter: TypeAdapter[HostPingResponse] = TypeAdapter(HostPingResponse)

    # Act
    result: DockerPingResponse | KubernetesPingResponse = adapter.validate_python(payload)

    # Assert
    assert result.type == expected_type
    assert result.status == "ok"


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        pytest.param(
            {"type": "docker", "keypair_id": str(_KEYPAIR_ID)},
            DockerHostUpdate,
            id="docker-credential",
        ),
        pytest.param(
            {"type": "kubernetes", "token": "replacement-token"},
            KubernetesHostUpdate,
            id="kubernetes-credential",
        ),
    ],
)
def test_host_update_010_nominal_partial_credential_update_is_selected_by_type(
    payload: dict[str, Any],
    expected_type: type[DockerHostUpdate] | type[KubernetesHostUpdate],
) -> None:
    """Test 010 - Nominal
    Condition: A partial update contains a provider discriminator and replacement credential
    Result: The matching update schema accepts only the supplied mutable field
    """
    # Arrange
    adapter: TypeAdapter[HostUpdate] = TypeAdapter(HostUpdate)

    # Act
    result: DockerHostUpdate | KubernetesHostUpdate = adapter.validate_python(payload)

    # Assert
    assert isinstance(result, expected_type)
    assert result.model_fields_set == set(payload)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"type": "docker", "name": None}, id="null-common-field"),
        pytest.param({"type": "docker", "port": None}, id="null-provider-field"),
        pytest.param(
            {"type": "kubernetes", "ca_cert_pem": None},
            id="null-certificate",
        ),
        pytest.param(
            {"type": "docker", "token": "wrong-provider"},
            id="wrong-provider-field",
        ),
        pytest.param(
            {"type": "kubernetes", "ca_cert_pem": "not-a-certificate"},
            id="invalid-ca",
        ),
    ],
)
def test_host_update_011_anomalous_invalid_partial_field_is_rejected(
    payload: dict[str, Any],
) -> None:
    """Test 011 - Anomalous
    Condition: A partial update has null, cross-provider, or invalid certificate data
    Result: ValidationError rejects the update before it reaches the service
    """
    # Arrange
    adapter: TypeAdapter[HostUpdate] = TypeAdapter(HostUpdate)

    # Act / Assert
    with pytest.raises(ValidationError):
        adapter.validate_python(payload)
