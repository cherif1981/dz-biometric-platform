"""AES-256-GCM field encryption. Key from MASTER_ENCRYPTION_KEY env (32-byte hex)."""
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class FieldCipher:
    def __init__(self, key_hex: str | None = None, key_id: str = "k1"):
        key_hex = key_hex or os.getenv("MASTER_ENCRYPTION_KEY")
        if not key_hex:
            raise ValueError("MASTER_ENCRYPTION_KEY not set (64 hex chars)")
        self.key = bytes.fromhex(key_hex)
        if len(self.key) != 32:
            raise ValueError("Key must be 32 bytes")
        self.aes = AESGCM(self.key)
        self.key_id = key_id
    def encrypt(self, plaintext: bytes, aad: bytes = b"") -> bytes:
        nonce = os.urandom(12)
        return nonce + self.aes.encrypt(nonce, plaintext, aad)
    def decrypt(self, blob: bytes, aad: bytes = b"") -> bytes:
        return self.aes.decrypt(blob[:12], blob[12:], aad)
