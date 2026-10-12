from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    FACE_MATCH_THRESHOLD: float = 0.45
    LIVENESS_THRESHOLD: float = 0.7
    OCR_LANGS: list[str] = ["ar", "fr", "en"]

    CORS_ORIGINS: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()