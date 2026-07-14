"""Tests for core.crypto."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from fourdrinier.core.crypto import (
    DecryptionError,
    EncryptionKeyError,
    FernetSecretCipher,
    decrypt_secret,
    encrypt_secret,
)
from fourdrinier.core.secrets import (
    EncryptedSecret,
    PlaintextSecret,
    SecretCipher,
    SecretConfigurationError,
    SecretDecryptionError,
)
from fourdrinier.core.settings import Settings


def _settings(key: str | None) -> Settings:
    return Settings(env="test", encryption_key=key)


def test_round_trip() -> None:
    settings = _settings(Fernet.generate_key().decode())
    token = encrypt_secret(b"secret material", settings)
    assert token != b"secret material"
    assert decrypt_secret(token, settings) == b"secret material"


def test_fernet_cipher_implements_secret_interface() -> None:
    cipher = FernetSecretCipher(Fernet.generate_key())
    plaintext = PlaintextSecret(b"provider credential")

    assert isinstance(cipher, SecretCipher)
    ciphertext = cipher.encrypt(plaintext)
    assert isinstance(ciphertext, bytes)
    assert ciphertext != plaintext
    assert cipher.decrypt(EncryptedSecret(ciphertext)) == plaintext


def test_missing_key_raises() -> None:
    with pytest.raises(SecretConfigurationError, match="ENCRYPTION_KEY is not set"):
        encrypt_secret(b"x", _settings(None))


def test_invalid_key_raises() -> None:
    with pytest.raises(EncryptionKeyError, match="not a valid Fernet key"):
        encrypt_secret(b"x", _settings("not-a-key"))


def test_wrong_key_raises_decryption_error() -> None:
    token = encrypt_secret(b"x", _settings(Fernet.generate_key().decode()))
    with pytest.raises(SecretDecryptionError):
        decrypt_secret(token, _settings(Fernet.generate_key().decode()))


def test_concrete_crypto_errors_keep_specific_diagnostics() -> None:
    assert issubclass(EncryptionKeyError, SecretConfigurationError)
    assert issubclass(DecryptionError, SecretDecryptionError)
