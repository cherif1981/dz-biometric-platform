"""
Deprecated shim. Re-exports from src.core.field_encryption.

SEC-04: Unified encryption module. Do NOT duplicate logic here.
Importing from here will be removed in a future release.
"""
from src.core.field_encryption import (  # noqa: F401
    EncryptionKeyMissing,
    decrypt_field,
    encrypt_field,
    rotate_key,
)

__all__ = [
    "encrypt_field",
    "decrypt_field",
    "rotate_key",
    "EncryptionKeyMissing",
]
