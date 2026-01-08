"""Application configuration."""

import logging
import secrets
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql+asyncpg://localhost/observer"

    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to async format for SQLAlchemy."""
        url = self.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Security - MUST be set via SECRET_KEY env variable in production
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS - stored as comma-separated string, parsed via property
    allowed_origins_str: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins(self) -> list[str]:
        """Parse allowed_origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins_str.split(",") if origin.strip()]

    # Claude API
    claude_oauth_token: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_proxy_url: str = "http://ccproxy.railway.internal:3001"
    ccproxy_internal_token: str = ""

    # App settings
    debug: bool = False
    environment: str = "development"

    @model_validator(mode="after")
    def validate_secret_key(self) -> "Settings":
        """Validate SECRET_KEY based on environment."""
        if not self.secret_key or self.secret_key == "":
            is_production = self.environment.lower() in ("production", "prod")

            if is_production:
                raise ValueError(
                    "SECRET_KEY must be set via environment variable in production. "
                    "Generate a secure key with: "
                    "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )

            # Development: generate random key with warning
            self.secret_key = secrets.token_urlsafe(32)
            logger.warning(
                "SECRET_KEY not set - generated random key for development. "
                "This key will change on restart. "
                "Set SECRET_KEY environment variable for persistence."
            )

        return self

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
