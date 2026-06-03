"""Application-level encryption for PII at rest (GDPR Art.32 / ISO 27001 A.10.1).

Uses Fernet (AES-128-CBC + HMAC-SHA256) with a key derived from
``ENCRYPTION_KEY`` (or ``SECRET_KEY`` as a development fallback). The derivation
accepts any high-entropy secret string and turns it into a valid Fernet key, so
operators don't have to generate a base64 key by hand.

``EncryptedString`` is a SQLAlchemy type that encrypts on write and decrypts on
read, transparently to the ORM. Decryption tolerates legacy plaintext values
(returns them as-is) so enabling encryption on an existing column never crashes.
"""
import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.types import TypeDecorator, Text

from app.core.config import settings


def _derive_key(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_key(settings.ENCRYPTION_KEY or settings.SECRET_KEY))


def encrypt_str(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_str(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # Legacy / not-yet-encrypted value — return unchanged.
        return token


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(token: bytes) -> bytes:
    try:
        return _fernet.decrypt(token)
    except (InvalidToken, ValueError):
        return token


class EncryptedString(TypeDecorator):
    """Transparently encrypted text column."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return encrypt_str(str(value))

    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        if value is None:
            return None
        return decrypt_str(value)
