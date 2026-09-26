from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "DZ Biometric Platform"
    app_version: str = "0.1.0"
    debug: bool = False

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Database
    database_url: str

    # Redis
    redis_url: str

    # AI
    ai_service_url: str = "http://ai-service:8001"

    # Storage
    storage_path: str = "/app/storage"

    # CORS
    cors_origins: list[str] = []


settings = Settings()