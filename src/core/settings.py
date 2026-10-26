"""إعدادات مركزية — ترفض أي قيمة افتراضية أو غير آمنة."""

import os
from typing import Any

INSECURE_VALUES = {
    "secret",
    "changeme",
    "password",
    "admin",
    "dev-secret",
    "default",
    "test",
    "123456",
}


class Settings:
    """بديل خفيف عن pydantic-settings لتجنب اعتماد إضافي داخل Colab."""

    def __init__(self, env: dict | None = None) -> None:
        env = env or os.environ
        self.jwt_secret = self._require(env, "JWT_SECRET")
        self.fernet_key = self._require(env, "FERNET_KEY")
        self.database_url = self._require(env, "DATABASE_URL")
        self.redis_url = self._require(env, "REDIS_URL")
        self._validate_fernet(self.fernet_key)

    @staticmethod
    def _require(env: dict, key: str) -> str:
        val = env.get(key, "").strip()
        if not val:
            raise RuntimeError(f"❌ {key} غير موجود في البيئة — رفض البدء (fail-fast).")
        if val.lower() in INSECURE_VALUES:
            raise RuntimeError(f"❌ {key} يحمل قيمة افتراضية غير آمنة: {val!r}.")
        if len(val) < 16 and key in ("JWT_SECRET", "FERNET_KEY"):
            raise RuntimeError(f"❌ {key} قصير جدًا ({len(val)} حرف) — الحد الأدنى 16.")
        return val

    @staticmethod
    def _validate_fernet(key: str) -> None:
        from cryptography.fernet import Fernet

        try:
            Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise RuntimeError(f"❌ FERNET_KEY غير صالح (يجب أن يكون 32 بايت base64-urlsafe): {e}")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
