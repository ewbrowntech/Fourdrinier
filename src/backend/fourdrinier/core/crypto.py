"""Symmetric encryption for secrets at rest (SSH private keys)."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from fourdrinier.core.settings import SETTINGS, Settings


class EncryptionKeyError(RuntimeError):
    """ENCRYPTION_KEY is missing or not a valid Fernet key."""


class DecryptionError(RuntimeError):
    """Ciphertext could not be decrypted with the configured key."""


def _fernet(settings: Settings) -> Fernet:
    if not settings.encryption_key:
        raise EncryptionKeyError(
            "ENCRYPTION_KEY is not set. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(settings.encryption_key)
    except (ValueError, TypeError) as exc:
        raise EncryptionKeyError("ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_secret(plaintext: bytes, settings: Settings | None = None) -> bytes:
    """Encrypt ``plaintext`` with the configured Fernet key."""
    return _fernet(settings or SETTINGS).encrypt(plaintext)


def decrypt_secret(token: bytes, settings: Settings | None = None) -> bytes:
    """Decrypt a Fernet ``token`` produced by :func:`encrypt_secret`."""
    try:
        return _fernet(settings or SETTINGS).decrypt(token)
    except InvalidToken as exc:
        raise DecryptionError(
            "stored secret could not be decrypted; ENCRYPTION_KEY may have changed"
        ) from exc


__all__ = ["DecryptionError", "EncryptionKeyError", "decrypt_secret", "encrypt_secret"]
