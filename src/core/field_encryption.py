"""
Field-level encryption for sensitive biometric data using Fernet.
"""

import base64
import json
import os

from cryptography.fernet import Fernet
from loguru import logger


class FieldEncryption:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        key = os.environ.get("ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            logger.warning("ENCRYPTION_KEY not set — using ephemeral key (dev only)")
        self.fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt_dict(self, data: dict) -> str:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        return self.fernet.encrypt(raw).decode("utf-8")

    def decrypt_dict(self, token: str) -> dict:
        raw = self.fernet.decrypt(token.encode("utf-8"))
        return json.loads(raw.decode("utf-8"))


def generate_key() -> str:
    return Fernet.generate_key().decode()


if __name__ == "__main__":
    print("🔑 New ENCRYPTION_KEY:", generate_key())
