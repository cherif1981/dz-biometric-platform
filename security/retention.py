"""Data retention + encrypted temp storage.

FIX: Fernet requires 32-byte base64-urlsafe key (44 chars).
We accept hex (64 chars) and encode internally.
"""
import base64
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


@dataclass
class RetentionPolicy:
    raw_image_ttl: int = 300           # 5 min
    temp_file_ttl: int = 3600          # 1 hour
    audit_retention_days: int = 365


def _hex_to_fernet_key(hex_key: str) -> bytes:
    """hex(64) -> bytes(32) -> base64-urlsafe(44)."""
    if len(hex_key) != 64:
        raise ValueError(f"hex key must be 64 chars, got {len(hex_key)}")
    raw = bytes.fromhex(hex_key)
    if len(raw) != 32:
        raise ValueError(f"decoded key must be 32 bytes, got {len(raw)}")
    return base64.urlsafe_b64encode(raw)


class SecureStorage:
    """Encrypted temporary file storage with TTL and secure deletion."""

    def __init__(self, base_dir: str, key_hex: str, policy: RetentionPolicy):
        os.makedirs(base_dir, exist_ok=True)
        os.chmod(base_dir, 0o700)
        self.base = base_dir
        self.policy = policy
        self._fernet = Fernet(_hex_to_fernet_key(key_hex))

    def _path(self, token: str) -> str:
        # Prevent path traversal
        safe = os.path.basename(token)
        return os.path.join(self.base, safe)

    def save(self, token: str, data: bytes) -> str:
        encrypted = self._fernet.encrypt(data)
        path = self._path(token)
        with open(path, "wb") as f:
            f.write(encrypted)
        os.chmod(path, 0o600)
        return path

    def read(self, token: str) -> bytes:
        try:
            with open(self._path(token), "rb") as f:
                return self._fernet.decrypt(f.read())
        except InvalidToken:
            raise ValueError("Invalid token or tampered file")

    def delete_now(self, token: str):
        path = self._path(token)
        if not os.path.exists(path):
            return
        size = os.path.getsize(path)
        with open(path, "wb") as f:
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
        os.remove(path)

    def sweep_expired(self) -> int:
        cutoff = time.time() - self.policy.temp_file_ttl
        n = 0
        for name in os.listdir(self.base):
            p = self._path(name)
            try:
                if os.path.getmtime(p) < cutoff:
                    self.delete_now(name)
                    n += 1
            except FileNotFoundError:
                pass
        return n


def audit_retention_cutoff(policy: RetentionPolicy) -> str:
    return (datetime.now(timezone.utc) -
            timedelta(days=policy.audit_retention_days)).isoformat()
