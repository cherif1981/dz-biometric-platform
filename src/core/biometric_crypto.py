"""Field-level encryption for biometric data (AES-256-GCM).

Design:
  - 32-byte key from BIOMETRIC_ENC_KEY env (base64) or /run/secrets/biometric_enc_key
  - 12-byte random nonce per encryption
  - AAD = b"biometric:v1" to bind ciphertext to purpose
  - Output = base64(nonce || ciphertext || tag)
  - Falls back to plaintext marker if key not configured (dev only) — logs warning once

Never store the key in the DB or in the same location as ciphertext.
"""
from __future__ import annotations

import base64
import os
import secrets
import logging
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

_AAD = b"biometric:v1"
_KEY: Optional[bytes] = None
_WARNED_NO_KEY = False


def _load_key() -> Optional[bytes]:
    """Load 32-byte key from env or secrets file. Cache it."""
    global _KEY, _WARNED_NO_KEY
    if _KEY is not None:
        return _KEY

    raw = os.getenv("BIOMETRIC_ENC_KEY")
    if not raw:
        # Try Docker secrets file
        try:
            with open("/run/secrets/biometric_enc_key", "r") as f:
                raw = f.read().strip()
        except (FileNotFoundError, PermissionError):
            raw = None

    if not raw:
        if not _WARNED_NO_KEY:
            logger.warning(
                "BIOMETRIC_ENC_KEY not set — biometric data will be stored "
                "PLAINTEXT. Set BIOMETRIC_ENC_KEY (base64 of 32 random bytes) "
                "in production."
            )
            _WARNED_NO_KEY = True
        return None

    try:
        key = base64.b64decode(raw)
    except Exception:
        raise ValueError("BIOMETRIC_ENC_KEY must be base64-encoded")

    if len(key) != 32:
        raise ValueError(
            f"BIOMETRIC_ENC_KEY must decode to 32 bytes, got {len(key)}"
        )

    _KEY = key
    return _KEY


def encrypt_biometric(plaintext: bytes) -> str:
    """Encrypt bytes → base64 string suitable for DB storage."""
    if not isinstance(plaintext, (bytes, bytearray)):
        raise TypeError("plaintext must be bytes")
    key = _load_key()
    if key is None:
        # Dev fallback: mark as plaintext so we can detect it later
        return "PLAINTEXT::" + base64.b64encode(bytes(plaintext)).decode("ascii")
    nonce = secrets.token_bytes(12)
    ct = AESGCM(key).encrypt(nonce, bytes(plaintext), _AAD)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_biometric(stored: str) -> bytes:
    """Decrypt base64 string → original bytes."""
    if stored.startswith("PLAINTEXT::"):
        return base64.b64decode(stored[len("PLAINTEXT::"):])
    key = _load_key()
    if key is None:
        raise RuntimeError(
            "Cannot decrypt: BIOMETRIC_ENC_KEY not set but ciphertext has no "
            "PLAINTEXT:: marker"
        )
    raw = base64.b64decode(stored)
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ct, _AAD)


def is_encrypted(stored: str) -> bool:
    """True if the value is ciphertext (not a PLAINTEXT:: dev fallback)."""
    return not stored.startswith("PLAINTEXT::")


def generate_key_b64() -> str:
    """Generate a fresh base64 key (for setup)."""
    return base64.b64encode(secrets.token_bytes(32)).decode("ascii")
