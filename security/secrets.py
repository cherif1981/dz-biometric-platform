"""Secrets loader: never hardcode secrets; fail loudly if missing.

Production: plug into HashiCorp Vault / AWS Secrets Manager / Azure Key Vault.
This module is the ONLY place that reads os.environ for secrets.
"""
import os
from dataclasses import dataclass
from typing import Optional


class SecretsError(Exception):
    """Raised when a required secret is missing or invalid."""


@dataclass
class AppSecrets:
    app_env: str                    # dev | staging | prod
    db_url: str                     # postgres://...
    redis_url: str                  # redis://...
    jwt_secret: str
    encryption_key_hex: str         # 32 bytes hex = 64 chars
    audit_db_url: str               # separate DB for audit log


class SecretsLoader:
    """Loads and validates secrets from environment. Never logs values."""

    REQUIRED = {
        "APP_ENV", "DATABASE_URL", "REDIS_URL",
        "JWT_SECRET", "ENCRYPTION_KEY_HEX", "AUDIT_DATABASE_URL",
    }

    @classmethod
    def load(cls) -> AppSecrets:
        try:
            from dotenv import load_dotenv
            load_dotenv(".env", override=False)  # .env not in git
        except ImportError:
            pass

        missing = [k for k in cls.REQUIRED if not os.environ.get(k)]
        if missing:
            raise SecretsError(
                f"Missing secrets: {missing}. "
                "Copy .env.example to .env and fill values, or configure "
                "your secrets manager (Vault/AWS/Azure)."
            )

        env = os.environ["APP_ENV"].lower()
        if env not in ("dev", "staging", "prod"):
            raise SecretsError(f"APP_ENV must be dev|staging|prod, got {env!r}")

        enc_key = os.environ["ENCRYPTION_KEY_HEX"]
        if len(enc_key) != 64:
            raise SecretsError("ENCRYPTION_KEY_HEX must be 64 hex chars (32 bytes)")
        try:
            bytes.fromhex(enc_key)
        except ValueError:
            raise SecretsError("ENCRYPTION_KEY_HEX is not valid hex")

        # Production hardening: JWT_SECRET must be long
        jwt = os.environ["JWT_SECRET"]
        if env == "prod" and len(jwt) < 32:
            raise SecretsError("JWT_SECRET must be >= 32 chars in prod")

        return AppSecrets(
            app_env=env,
            db_url=os.environ["DATABASE_URL"],
            redis_url=os.environ["REDIS_URL"],
            jwt_secret=jwt,
            encryption_key_hex=enc_key,
            audit_db_url=os.environ["AUDIT_DATABASE_URL"],
        )

    @classmethod
    def generate_env_example(cls) -> str:
        return """# .env.example — copy to .env, NEVER commit .env
APP_ENV=dev
DATABASE_URL=postgresql://user:pass@localhost:5432/appdb
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-to-a-32-char-minimum-random-string
ENCRYPTION_KEY_HEX=0000000000000000000000000000000000000000000000000000000000000000
AUDIT_DATABASE_URL=postgresql://user:pass@localhost:5432/auditdb
"""
