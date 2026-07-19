"""Fernet implementation of the secret-handling interfaces."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from fourdrinier.core.secrets import (
    EncryptedSecret,
    PlaintextSecret,
    SecretCipher,
    SecretConfigurationError,
    SecretDecryptionError,
)
from fourdrinier.core.settings import SETTINGS, Settings


class EncryptionKeyError(SecretConfigurationError):
    """ENCRYPTION_KEY is missing or not a valid Fernet key."""


class DecryptionError(SecretDecryptionError):
    """Ciphertext could not be decrypted with the configured key."""


class FernetSecretCipher(SecretCipher):
    """Encrypt secrets using one configured Fernet key."""

    def __init__(self, key: str | bytes) -> None:
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise EncryptionKeyError("ENCRYPTION_KEY is not a valid Fernet key") from exc

    @classmethod
    def from_settings(cls, settings: Settings) -> FernetSecretCipher:
        """Build a cipher from application settings."""
        if not settings.encryption_key:
            raise EncryptionKeyError(
                "ENCRYPTION_KEY is not set. Generate one with: "
                'python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        return cls(settings.encryption_key)

    def encrypt(self, plaintext: PlaintextSecret, /) -> EncryptedSecret:
        return EncryptedSecret(self._fernet.encrypt(plaintext))

    def decrypt(self, ciphertext: EncryptedSecret, /) -> PlaintextSecret:
        try:
            return PlaintextSecret(self._fernet.decrypt(ciphertext))
        except InvalidToken as exc:
            raise DecryptionError(
                "stored secret could not be decrypted; ENCRYPTION_KEY may have changed"
            ) from exc


def encrypt_secret(plaintext: bytes, settings: Settings | None = None) -> bytes:
    """Encrypt ``plaintext`` with the configured Fernet key."""
    cipher = FernetSecretCipher.from_settings(settings or SETTINGS)
    return cipher.encrypt(PlaintextSecret(plaintext))


def decrypt_secret(token: bytes, settings: Settings | None = None) -> bytes:
    """Decrypt a Fernet ``token`` produced by :func:`encrypt_secret`."""
    cipher = FernetSecretCipher.from_settings(settings or SETTINGS)
    return cipher.decrypt(EncryptedSecret(token))


__all__ = [
    "DecryptionError",
    "EncryptionKeyError",
    "FernetSecretCipher",
    "decrypt_secret",
    "encrypt_secret",
]
