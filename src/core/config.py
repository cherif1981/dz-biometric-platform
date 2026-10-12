from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_INSECURE = {
    "change-me-in-production",
    "change-me",
    "changeme",
    "secret",
    "",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "DZ Biometric Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # SEC-03: SECRET_KEY إلزامي في الإنتاج
    SECRET_KEY: SecretStr = Field(
        default=SecretStr("change-me-in-production"),
        description="JWT signing secret. MUST be set in production.",
    )
    JWT_ALGORITHM: str = Field(default="HS256", frozen=True)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SEC-04: مفتاح تشفير الحقول
    FIELD_ENCRYPTION_KEY: SecretStr | None = None

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./dz_biometric.db",
        description="Database URL. MUST be PostgreSQL in production.",
    )
    REDIS_URL: str = "redis://localhost:6379/0"

    # ML thresholds
    FACE_MATCH_THRESHOLD: float = 0.40
    LIVENESS_THRESHOLD: float = 0.50
    ANTISPOOF_THRESHOLD: float = 0.45
    OCR_LANGS: list[str] = ["ar", "fr", "en"]

    # SEC-10: CORS فارغة افتراضياً
    CORS_ORIGINS: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def _accept_legacy_jwt_secret_key(cls, data):
        if isinstance(data, dict):
            if "SECRET_KEY" not in data and "JWT_SECRET_KEY" in data:
                data["SECRET_KEY"] = data.pop("JWT_SECRET_KEY")
        return data

    @model_validator(mode="after")
    def _enforce_production_safety(self):
        if self.ENVIRONMENT != "production":
            return self

        secret = self.SECRET_KEY.get_secret_value()
        if secret in _DEFAULT_INSECURE:
            raise ValueError(
                "SECRET_KEY is still the default value. "
                "Generate one with: openssl rand -hex 32"
            )
        if len(secret) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 chars in production"
            )

        if self.DATABASE_URL.startswith("sqlite"):
            raise ValueError(
                "SQLite is not allowed in production. "
                "Set DATABASE_URL to PostgreSQL."
            )
        if "user:pass@" in self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL contains placeholder credentials"
            )

        if not self.FIELD_ENCRYPTION_KEY:
            raise ValueError("FIELD_ENCRYPTION_KEY is required in production")

        if "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS cannot contain '*' in production"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
