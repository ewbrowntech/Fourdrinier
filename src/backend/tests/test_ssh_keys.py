"""Tests for hosts.ssh.keys."""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from fourdrinier.hosts.ssh.keys import (
    PassphraseProtectedKeyError,
    PrivateKeyError,
    generate_keypair,
    import_private_key,
)


def test_generate_keypair_is_ed25519() -> None:
    material = generate_keypair()
    assert material.algorithm == "ed25519"
    assert material.public_key.startswith("ssh-ed25519 ")
    assert material.fingerprint.startswith("SHA256:")
    assert "PRIVATE KEY" in material.private_key_pem


def test_import_round_trips_generated_key() -> None:
    generated = generate_keypair()
    imported = import_private_key(generated.private_key_pem)
    assert imported.public_key == generated.public_key
    assert imported.fingerprint == generated.fingerprint


def test_import_garbage_raises() -> None:
    with pytest.raises(PrivateKeyError):
        import_private_key("definitely not a key")


def test_import_passphrase_protected_raises() -> None:
    encrypted_pem = (
        ed25519.Ed25519PrivateKey.generate()
        .private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.OpenSSH,
            serialization.BestAvailableEncryption(b"passphrase"),
        )
        .decode()
    )
    with pytest.raises(PassphraseProtectedKeyError):
        import_private_key(encrypted_pem)
