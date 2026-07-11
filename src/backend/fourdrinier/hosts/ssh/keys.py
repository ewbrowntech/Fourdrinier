"""Generate and import SSH keypairs; all private-key handling stays in memory."""

from __future__ import annotations

import io
from dataclasses import dataclass

import paramiko
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class PrivateKeyError(ValueError):
    """The provided private key could not be parsed."""


class PassphraseProtectedKeyError(PrivateKeyError):
    """The provided private key is passphrase-protected (unsupported)."""


_KEY_CLASSES: tuple[type[paramiko.PKey], ...] = (
    paramiko.Ed25519Key,
    paramiko.ECDSAKey,
    paramiko.RSAKey,
)

_ALGORITHM_BY_KEY_NAME: dict[str, str] = {
    "ssh-ed25519": "ed25519",
    "ssh-rsa": "rsa",
    "ecdsa-sha2-nistp256": "ecdsa",
    "ecdsa-sha2-nistp384": "ecdsa",
    "ecdsa-sha2-nistp521": "ecdsa",
}


@dataclass(frozen=True)
class KeypairMaterial:
    """Parsed keypair: private PEM plus derived public metadata."""

    private_key_pem: str
    public_key: str
    fingerprint: str
    algorithm: str


def _material_from_pkey(pkey: paramiko.PKey, private_key_pem: str) -> KeypairMaterial:
    key_name: str = pkey.get_name()
    return KeypairMaterial(
        private_key_pem=private_key_pem,
        public_key=f"{key_name} {pkey.get_base64()}",
        fingerprint=pkey.fingerprint,
        algorithm=_ALGORITHM_BY_KEY_NAME.get(key_name, key_name),
    )


def load_pkey(private_key_pem: str) -> paramiko.PKey:
    """Parse a private key (OpenSSH or PEM encoded) into a paramiko key.

    Raises:
        PassphraseProtectedKeyError: key requires a passphrase.
        PrivateKeyError: key could not be parsed by any supported algorithm.
    """
    for key_cls in _KEY_CLASSES:
        try:
            return key_cls.from_private_key(io.StringIO(private_key_pem))
        except paramiko.PasswordRequiredException as exc:
            raise PassphraseProtectedKeyError(
                "passphrase-protected private keys are not supported"
            ) from exc
        except paramiko.SSHException:
            continue
    raise PrivateKeyError(
        "could not parse private key; expected an unencrypted ed25519, ECDSA, "
        "or RSA key in OpenSSH or PEM format"
    )


def generate_keypair() -> KeypairMaterial:
    """Generate a new ed25519 keypair."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    private_key_pem: str = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    ).decode()
    pkey: paramiko.PKey = load_pkey(private_key_pem)
    return _material_from_pkey(pkey, private_key_pem)


def import_private_key(private_key_pem: str) -> KeypairMaterial:
    """Parse an uploaded private key and derive its public metadata."""
    pkey: paramiko.PKey = load_pkey(private_key_pem)
    return _material_from_pkey(pkey, private_key_pem)


__all__ = [
    "KeypairMaterial",
    "PassphraseProtectedKeyError",
    "PrivateKeyError",
    "generate_keypair",
    "import_private_key",
    "load_pkey",
]
