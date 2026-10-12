from cryptography.fernet import Fernet
from src.core.config import settings
from src.core.exceptions import AppError


class FieldEncryptor:
    def __init__(self, key: str | None = None):
        key = key or settings.FIELD_ENCRYPTION_KEY
        if not key:
            # generate ephemeral for dev
            key = Fernet.generate_key().decode()
        self._f = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        if plaintext is None:
            return None
        return self._f.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        if token is None:
            return None
        try:
            return self._f.decrypt(token.encode()).decode()
        except Exception as e:
            raise AppError("decryption_failed", {"reason": str(e)})