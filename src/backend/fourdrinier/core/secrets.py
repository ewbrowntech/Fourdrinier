"""Interfaces and value types for handling encrypted secret material."""

from __future__ import annotations

from typing import NewType, Protocol, runtime_checkable


PlaintextSecret = NewType("PlaintextSecret", bytes)
EncryptedSecret = NewType("EncryptedSecret", bytes)


class SecretError(RuntimeError):
    """Base class for secret-handling failures."""


class SecretConfigurationError(SecretError):
    """The configured secret encryption mechanism cannot be initialized."""


class SecretDecryptionError(SecretError):
    """Stored secret material cannot be decrypted."""


@runtime_checkable
class SecretEncryptor(Protocol):
    """Encrypt plaintext secret bytes for persistence."""

    def encrypt(self, plaintext: PlaintextSecret, /) -> EncryptedSecret: ...


@runtime_checkable
class SecretDecryptor(Protocol):
    """Recover plaintext secret bytes for provider use."""

    def decrypt(self, ciphertext: EncryptedSecret, /) -> PlaintextSecret: ...


@runtime_checkable
class SecretCipher(SecretEncryptor, SecretDecryptor, Protocol):
    """Combined interface used where both secret operations are required."""


__all__ = [
    "EncryptedSecret",
    "PlaintextSecret",
    "SecretCipher",
    "SecretConfigurationError",
    "SecretDecryptionError",
    "SecretDecryptor",
    "SecretEncryptor",
    "SecretError",
]
