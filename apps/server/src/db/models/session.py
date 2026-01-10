"""Session model for tracking user work sessions."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import JSONType, PortableUUID, StringArray


class Session(Base):
    """User work session tracking."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    device_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("devices.id"),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime())
    duration_minutes: Mapped[float | None] = mapped_column(Float)
    apps_used: Mapped[list[str]] = mapped_column(StringArray(), default=list)
    events_count: Mapped[int] = mapped_column(Integer, default=0)
    productivity_score: Mapped[float | None] = mapped_column(Float)
    session_metadata: Mapped[dict[str, Any]] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    __table_args__ = (
        Index("idx_sessions_device_time", "device_id", "start_time"),
        Index("idx_sessions_start_time", "start_time"),
        Index("idx_sessions_end_time", "end_time"),
    )
