from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import model_validator, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "DZ Biometric Platform"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Field-level encryption (Fernet key)
    FIELD_ENCRYPTION_KEY: str = ""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/dz_biometric"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ML
    OCR_LANGS: list[str] = ["ar", "fr", "en"]

    CORS_ORIGINS: list[str] = ["*"]

    @model_validator(mode="after")
    def _validate_production_secrets(self):
        if not getattr(self, "DEBUG", True):
            if not getattr(self, "FIELD_ENCRYPTION_KEY", None):
                raise ValueError("FIELD_ENCRYPTION_KEY must be set in production")
            if getattr(self, "SECRET_KEY", "") in ("", "change-me-in-production"):
                raise ValueError("SECRET_KEY must be a strong value in production")
        return self

    @property
    def thresholds(self) -> dict:
        import yaml, pathlib
        f = pathlib.Path(__file__).resolve().parents[2] / "config" / "thresholds.yaml"
        return yaml.safe_load(f.read_text())


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
