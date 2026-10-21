from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import model_validator
from pydantic_settings import SettingsConfigDict


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

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @model_validator(mode="after")
    def _validate_production_secrets(self):
        """Fail-fast validation for production configuration."""
        if self.DEBUG:
            return self
        errors = []
        if not self.FIELD_ENCRYPTION_KEY:
            errors.append("FIELD_ENCRYPTION_KEY must be set")
        if self.SECRET_KEY in ("", "change-me-in-production"):
            errors.append("SECRET_KEY must not be default/empty")
        elif len(self.SECRET_KEY) < 32:
            errors.append("SECRET_KEY must be >= 32 chars")
        if not self.CORS_ORIGINS:
            errors.append("CORS_ORIGINS must be explicit (not empty)")
        elif "*" in self.CORS_ORIGINS:
            errors.append("CORS_ORIGINS must not contain '*' in production")
        if "user:pass@" in self.DATABASE_URL:
            errors.append("DATABASE_URL must not use placeholder credentials")
        if errors:
            raise ValueError("production config invalid: " + "; ".join(errors))
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
