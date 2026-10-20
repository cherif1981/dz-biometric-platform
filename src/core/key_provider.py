"""واجهة موحدة لإدارة المفاتيح.

EnvKeyProvider: للتطوير (FERNET_KEY من environment)
VaultKeyProvider: للإنتاج (HashiCorp Vault / AWS KMS / GCP KMS)
"""
import os
from abc import ABC, abstractmethod
from cryptography.fernet import Fernet


class KeyProvider(ABC):
    @abstractmethod
    def get_data_key(self) -> bytes: ...

    @abstractmethod
    def rotate(self) -> None: ...


class EnvKeyProvider(KeyProvider):
    """للتطوير فقط — يقرأ من FERNET_KEY. غير آمن للإنتاج (لا دوران، مفتاح واحد)."""

    def __init__(self):
        key = os.environ.get("FERNET_KEY", "")
        if not key:
            raise RuntimeError("FERNET_KEY غير موجود في البيئة")
        self._key = key.encode() if isinstance(key, str) else key
        Fernet(self._key)  # تحقق من الصلاحية

    def get_data_key(self) -> bytes:
        return self._key

    def rotate(self) -> None:
        raise NotImplementedError(
            "EnvKeyProvider لا يدعم الدوران. استخدم KMS/Vault للإنتاج."
        )


class VaultKeyProvider(KeyProvider):
    """stub — يُستكمل عند نشر HashiCorp Vault أو AWS/GCP KMS."""

    def __init__(self, vault_url: str, token: str, key_name: str):
        self.vault_url = vault_url
        self.token = token
        self.key_name = key_name

    def get_data_key(self) -> bytes:
        raise NotImplementedError(
            "يُستكمل بـ hvac.transit.decrypt() أو boto3 kms.decrypt()."
        )

    def rotate(self) -> None:
        raise NotImplementedError(
            "يُستكمل بـ hvac.transit.rotate_key() أو kms.rotate_key()."
        )


def get_key_provider() -> KeyProvider:
    """يختار المزوّد حسب المتغير KMS_BACKEND (env افتراضيًا)."""
    backend = os.environ.get("KMS_BACKEND", "env").lower()
    if backend == "vault":
        return VaultKeyProvider(
            vault_url=os.environ["VAULT_URL"],
            token=os.environ["VAULT_TOKEN"],
            key_name=os.environ.get("VAULT_KEY_NAME", "dz-biometric"),
        )
    return EnvKeyProvider()
