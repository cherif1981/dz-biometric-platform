from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DZ Biometric Platform"
    debug: bool = False

    database_url: str = "postgresql://dzuser:dzpass@postgres:5432/dzbiometric"
    redis_url: str = "redis://redis:6379/0"

    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    ai_service_url: str = "http://ai-service:8001"
    storage_path: str = "/app/storage"


settings = Settings()