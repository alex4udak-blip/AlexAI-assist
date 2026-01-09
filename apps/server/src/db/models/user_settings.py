"""User settings model."""

from datetime import datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserSettings(Base):
    """User settings storage."""

    __tablename__ = "user_settings"

    device_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    settings: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)
