"""
test_crypto.py

Unit tests for the Fernet secret cipher.
"""

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
from fourdrinier.core.secrets import EncryptedSecret, PlaintextSecret, SecretCipher
from fourdrinier.core.settings import Settings


def _settings(key: str | None) -> Settings:
    return Settings(env="test", encryption_key=key)


def test_encrypt_secret_001_nominal_plaintext_is_encrypted_and_decrypted() -> None:
    """Test 001 - Nominal
    Condition: A valid Fernet key and plaintext secret are supplied
    Result: The encrypted bytes differ from the plaintext and decrypt to the original value
    """
    # Arrange
    settings: Settings = _settings(Fernet.generate_key().decode())
    plaintext: bytes = b"secret material"

    # Act
    token: bytes = encrypt_secret(plaintext, settings)
    decrypted: bytes = decrypt_secret(token, settings)

    # Assert
    assert token != plaintext
    assert decrypted == plaintext


def test_fernet_secret_cipher_002_nominal_cipher_satisfies_secret_contract() -> None:
    """Test 002 - Nominal
    Condition: A Fernet cipher is initialized with a valid key
    Result: It satisfies SecretCipher and round-trips typed secret values
    """
    # Arrange
    cipher: FernetSecretCipher = FernetSecretCipher(Fernet.generate_key())
    plaintext: PlaintextSecret = PlaintextSecret(b"provider credential")

    # Act
    ciphertext: EncryptedSecret = cipher.encrypt(plaintext)
    decrypted: PlaintextSecret = cipher.decrypt(ciphertext)

    # Assert
    assert isinstance(cipher, SecretCipher)
    assert ciphertext != plaintext
    assert decrypted == plaintext


def test_fernet_secret_cipher_003_anomalous_encryption_key_is_missing() -> None:
    """Test 003 - Anomalous
    Condition: The encryption key setting is missing
    Result: EncryptionKeyError is raised with the missing-key diagnostic
    """
    # Arrange
    settings: Settings = _settings(None)
    expected_message: str = (
        "ENCRYPTION_KEY is not set. Generate one with: "
        'python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"'
    )
    captured: pytest.ExceptionInfo[EncryptionKeyError]

    # Act
    with pytest.raises(EncryptionKeyError) as captured:
        encrypt_secret(b"secret material", settings)

    # Assert
    assert str(captured.value) == expected_message


def test_fernet_secret_cipher_004_anomalous_encryption_key_is_invalid() -> None:
    """Test 004 - Anomalous
    Condition: The encryption key setting is not a valid Fernet key
    Result: EncryptionKeyError("ENCRYPTION_KEY is not a valid Fernet key") is raised
    """
    # Arrange
    settings: Settings = _settings("not-a-key")
    captured: pytest.ExceptionInfo[EncryptionKeyError]

    # Act
    with pytest.raises(EncryptionKeyError) as captured:
        encrypt_secret(b"secret material", settings)

    # Assert
    assert str(captured.value) == "ENCRYPTION_KEY is not a valid Fernet key"


def test_fernet_secret_cipher_005_anomalous_ciphertext_uses_another_key() -> None:
    """Test 005 - Anomalous
    Condition: Ciphertext is decrypted with a different valid Fernet key
    Result: DecryptionError is raised with the changed-key diagnostic
    """
    # Arrange
    encrypt_settings: Settings = _settings(Fernet.generate_key().decode())
    decrypt_settings: Settings = _settings(Fernet.generate_key().decode())
    token: bytes = encrypt_secret(b"secret material", encrypt_settings)
    captured: pytest.ExceptionInfo[DecryptionError]

    # Act
    with pytest.raises(DecryptionError) as captured:
        decrypt_secret(token, decrypt_settings)

    # Assert
    assert (
        str(captured.value)
        == "stored secret could not be decrypted; ENCRYPTION_KEY may have changed"
    )
