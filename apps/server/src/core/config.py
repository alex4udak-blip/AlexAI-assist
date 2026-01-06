"""Application configuration."""

from functools import lru_cache
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings


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

    # Security
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse allowed_origins from comma-separated string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Claude API
    claude_oauth_token: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # App settings
    debug: bool = False
    environment: str = "development"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
