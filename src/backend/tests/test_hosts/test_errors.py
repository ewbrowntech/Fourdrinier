"""
test_errors.py

Unit tests for provider-neutral host errors.
"""

from __future__ import annotations

from fourdrinier.hosts.errors import (
    HostAuthenticationError,
    HostError,
    HostRemoteError,
)
from fourdrinier.hosts.types import HostType


def test_host_authentication_error_001_nominal_remote_failure_is_described() -> None:
    """Test 001 - Nominal
    Condition: Kubernetes reports an authentication failure with a diagnostic message
    Result: The stable remote error retains its provider, hierarchy, and message
    """
    # Arrange
    message: str = "remote credentials were rejected"
    provider: HostType = HostType.KUBERNETES

    # Act
    error: HostAuthenticationError = HostAuthenticationError(message, provider=provider)

    # Assert
    assert isinstance(error, HostRemoteError)
    assert isinstance(error, HostError)
    assert error.provider is provider
    assert str(error) == message
