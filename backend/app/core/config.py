from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, model_validator
from typing import List, Optional
import os
import secrets


class Settings(BaseSettings):
    PROJECT_NAME: str = "KYC/AML Risk Assessment Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # "development" | "staging" | "production". In production the app refuses
    # to start with insecure default secrets (see _enforce_production_secrets).
    ENVIRONMENT: str = "development"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    # Separate key for field/file encryption at rest. Falls back to SECRET_KEY
    # in development; must be set explicitly in production.
    ENCRYPTION_KEY: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # --- Authentication hardening (ISO 27001 A.9.4.2 / OWASP ASVS V2) ---
    MAX_LOGIN_ATTEMPTS: int = 5          # failed logins before temporary lockout
    ACCOUNT_LOCKOUT_MINUTES: int = 15    # how long the account stays locked

    # --- HTTP hardening ---
    # Host header allow-list. ["*"] disables the TrustedHost check (dev only).
    ALLOWED_HOSTS: List[str] = ["*"]
    # Emit HSTS header (enable only when served strictly over HTTPS).
    ENABLE_HSTS: bool = False

    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "kyc_aml_db"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REDIS_URL: str = "redis://localhost:6379"

    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ]

    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_DOCUMENT_TYPES: List[str] = ["image/jpeg", "image/png", "application/pdf"]

    FIRST_SUPERUSER_EMAIL: str = "admin@kyc-platform.com"
    FIRST_SUPERUSER_PASSWORD: str = "Admin123!@#"

    @model_validator(mode="after")
    def _enforce_production_secrets(self):
        """Fail fast if the app is started in production with insecure defaults.

        Covers ISO 27001 A.9.2.4 (management of secret authentication information)
        and OWASP ASVS V6 (stored cryptographic secrets must not be hard-coded).
        """
        if self.ENVIRONMENT.lower() == "production":
            problems = []
            if not os.getenv("SECRET_KEY"):
                problems.append("SECRET_KEY must be provided via environment")
            if self.POSTGRES_PASSWORD in ("postgres", "your_secure_password", ""):
                problems.append("POSTGRES_PASSWORD must not use a default value")
            if self.FIRST_SUPERUSER_PASSWORD in ("Admin123!@#", ""):
                problems.append("FIRST_SUPERUSER_PASSWORD must be changed")
            if self.ALLOWED_HOSTS == ["*"]:
                problems.append("ALLOWED_HOSTS must be an explicit allow-list")
            if not os.getenv("ENCRYPTION_KEY"):
                problems.append("ENCRYPTION_KEY must be provided via environment")
            if problems:
                raise ValueError(
                    "Insecure production configuration: " + "; ".join(problems)
                )
        return self

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
