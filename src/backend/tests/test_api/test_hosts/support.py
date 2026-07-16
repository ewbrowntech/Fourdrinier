"""
support.py

Provide reusable certificate and credential data for host integration tests.
"""

from __future__ import annotations

from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import NameOID


def _make_ca_pem() -> str:
    key: ed25519.Ed25519PrivateKey = ed25519.Ed25519PrivateKey.generate()
    subject: x509.Name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
    valid_from: datetime = datetime(2020, 1, 1, tzinfo=UTC)
    valid_until: datetime = datetime(2100, 1, 1, tzinfo=UTC)
    certificate: x509.Certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(valid_from)
        .not_valid_after(valid_until)
        .sign(key, algorithm=None)
    )
    return certificate.public_bytes(Encoding.PEM).decode()


CA_PEM: str = _make_ca_pem()
FAKE_TOKEN: str = "eyJhbGciOiJSUzI1NiJ9.fake.token"
