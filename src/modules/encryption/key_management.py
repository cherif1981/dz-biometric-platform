import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_aes_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode()


def unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode())


def new_nonce() -> bytes:
    return os.urandom(12)