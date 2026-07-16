"""
test_keys.py

Unit tests for SSH keypair generation and import.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from fourdrinier.hosts.ssh.keys import (
    KeypairMaterial,
    PassphraseProtectedKeyError,
    PrivateKeyError,
    generate_keypair,
    import_private_key,
)


def test_generate_keypair_001_nominal_ed25519_material_is_returned() -> None:
    """Test 001 - Nominal
    Condition: A new SSH keypair is requested
    Result: Generated Ed25519 private and public metadata are returned
    """
    # Arrange
    expected_algorithm: str = "ed25519"

    # Act
    material: KeypairMaterial = generate_keypair()

    # Assert
    assert material.algorithm == expected_algorithm
    assert material.public_key.startswith("ssh-ed25519 ")
    assert material.fingerprint.startswith("SHA256:")
    assert "PRIVATE KEY" in material.private_key_pem


def test_import_private_key_002_nominal_generated_key_is_imported() -> None:
    """Test 002 - Nominal
    Condition: A generated unencrypted Ed25519 private key is supplied
    Result: Its public key and fingerprint are derived without changing the private key
    """
    # Arrange
    generated: KeypairMaterial = generate_keypair()

    # Act
    imported: KeypairMaterial = import_private_key(generated.private_key_pem)

    # Assert
    assert imported.private_key_pem == generated.private_key_pem
    assert imported.public_key == generated.public_key
    assert imported.fingerprint == generated.fingerprint
    assert imported.algorithm == generated.algorithm


def test_import_private_key_003_anomalous_key_material_is_unparseable() -> None:
    """Test 003 - Anomalous
    Condition: The supplied text is not SSH private-key material
    Result: PrivateKeyError is raised with the supported-format diagnostic
    """
    # Arrange
    private_key_pem: str = "definitely not a key"
    captured: pytest.ExceptionInfo[PrivateKeyError]

    # Act
    with pytest.raises(PrivateKeyError) as captured:
        import_private_key(private_key_pem)

    # Assert
    assert str(captured.value) == (
        "could not parse private key; expected an unencrypted ed25519, ECDSA, "
        "or RSA key in OpenSSH or PEM format"
    )


def test_import_private_key_004_anomalous_key_requires_passphrase() -> None:
    """Test 004 - Anomalous
    Condition: The supplied Ed25519 private key is protected by a passphrase
    Result: PassphraseProtectedKeyError is raised with the unsupported-key diagnostic
    """
    # Arrange
    private_key: ed25519.Ed25519PrivateKey = ed25519.Ed25519PrivateKey.generate()
    private_key_pem: str = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.BestAvailableEncryption(b"passphrase"),
    ).decode()
    captured: pytest.ExceptionInfo[PassphraseProtectedKeyError]

    # Act
    with pytest.raises(PassphraseProtectedKeyError) as captured:
        import_private_key(private_key_pem)

    # Assert
    assert str(captured.value) == "passphrase-protected private keys are not supported"
