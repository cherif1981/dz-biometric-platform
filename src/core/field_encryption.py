"""
Field-level encryption using Fernet (AES-128-CBC + HMAC-SHA256).

SEC-04: The encryption key is MANDATORY in production.
A missing key raises at import time instead of silently generating
an ephemeral key that would silently make data unrecoverable.

Key generation:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import logging
import warnings
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from src.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionKeyMissing(RuntimeError):
    """Raised when FIELD_ENCRYPTION_KEY is required but missing/invalid."""


def _coerce_key(key) -> str:
    if key is None:
        return ""
    if hasattr(key, "get_secret_value"):
        return key.get_secret_value()
    return str(key)


def _load_key() -> bytes:
    """Return the Fernet key as bytes. Enforces production safety."""
    key_str = _coerce_key(getattr(settings, "FIELD_ENCRYPTION_KEY", None))

    if key_str:
        try:
            Fernet(key_str.encode())
            return key_str.encode()
        except Exception as e:
            raise EncryptionKeyMissing(
                f"FIELD_ENCRYPTION_KEY is malformed: {e}. "
                "Regenerate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            ) from e

    # No key provided
    env = getattr(settings, "ENVIRONMENT", "development")
    if env == "production":
        raise EncryptionKeyMissing(
            "FIELD_ENCRYPTION_KEY is required in production. "
            "Generate one and set it in the environment."
        )

    warnings.warn(
        "FIELD_ENCRYPTION_KEY not set. Generating an EPHEMERAL key. "
        "Data encrypted now will be UNRECOVERABLE after restart. "
        "Set FIELD_ENCRYPTION_KEY to persist across restarts.",
        RuntimeWarning,
        stacklevel=2,
    )
    logger.warning("Using ephemeral FIELD_ENCRYPTION_KEY (dev only)")
    return Fernet.generate_key()


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    return Fernet(_load_key())


def encrypt_field(plaintext: str) -> str:
    """Encrypt a string. Returns URL-safe base64 Fernet token."""
    if plaintext is None:
        raise ValueError("Cannot encrypt None")
    if not isinstance(plaintext, str):
        raise TypeError(f"Expected str, got {type(plaintext).__name__}")
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_field(ciphertext: str) -> str:
    """Decrypt a Fernet token. Raises ValueError on tampering."""
    if not isinstance(ciphertext, str):
        raise TypeError(f"Expected str, got {type(ciphertext).__name__}")
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Invalid or tampered ciphertext") from e


def rotate_key(new_key: str, ciphertext: str) -> str:
    """
    Decrypt with the current key, then re-encrypt with new_key.
    Use this during key rotation to migrate stored ciphertexts.
    """
    plain = decrypt_field(ciphertext)
    new_fernet = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
    return new_fernet.encrypt(plain.encode("utf-8")).decode("ascii")
