"""تشفير البيانات البيومترية — Fernet (AES-128 + HMAC)."""
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_key() -> bytes:
    """يجلب مفتاح التشفير من config/env."""
    key = settings.biometric_encryption_key or os.environ.get("BIOMETRIC_ENCRYPTION_KEY")
    if key:
        return key.encode() if isinstance(key, str) else key

    # للتطوير فقط — لا تستخدم هذا في الإنتاج!
    generated = Fernet.generate_key()
    os.environ["BIOMETRIC_ENCRYPTION_KEY"] = generated.decode()
    print("⚠️ تم توليد BIOMETRIC_ENCRYPTION_KEY جديد (للتطوير فقط)")
    return generated


_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_key())
    return _fernet


def encrypt_bytes(data: bytes) -> Optional[bytes]:
    if data is None:
        return None
    return _get_fernet().encrypt(data)


def decrypt_bytes(token: bytes) -> Optional[bytes]:
    if token is None:
        return None
    try:
        return _get_fernet().decrypt(token)
    except InvalidToken:
        return None


def encrypt_str(text: str) -> Optional[str]:
    if text is None:
        return None
    return _get_fernet().encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt_str(token: str) -> Optional[str]:
    if token is None:
        return None
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None
