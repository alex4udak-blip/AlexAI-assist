"""Automation state models for persistent storage."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


def utc_now() -> datetime:
    """Get current UTC time as naive datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid4())


class DeviceStatus(Base):
    """Device status and connection state."""

    __tablename__ = "device_statuses"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_uuid
    )
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="idle")
    last_seen_at: Mapped[datetime | None] = mapped_column()
    last_sync_at: Mapped[datetime | None] = mapped_column()
    status_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class CommandResult(Base):
    """Command execution result for persistence."""

    __tablename__ = "command_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # command_id
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command_type: Mapped[str] = mapped_column(String(100), nullable=False)
    command_params: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    success: Mapped[bool | None] = mapped_column(Boolean)
    result_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column()


class Screenshot(Base):
    """Screenshot history for devices."""

    __tablename__ = "screenshots"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_uuid
    )
    device_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("command_results.id", ondelete="SET NULL")
    )
    screenshot_data: Mapped[str] = mapped_column(Text, nullable=False)  # base64
    ocr_text: Mapped[str | None] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)


class Feedback(Base):
    """User feedback for system evolution."""

    __tablename__ = "feedbacks"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=generate_uuid
    )
    feedback_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # thumbs_up, thumbs_down, rating, comment
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))  # response_quality, accuracy
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # session_id, message_id, etc.
    session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    message_id: Mapped[str | None] = mapped_column(String(64))
    agent_id: Mapped[str | None] = mapped_column(String(64))
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, index=True)
