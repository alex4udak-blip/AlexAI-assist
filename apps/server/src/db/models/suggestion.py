"""Suggestion model."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import JSONType, PortableUUID


class Suggestion(Base):
    """Automation suggestion based on detected patterns."""

    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID(),
        ForeignKey("patterns.id"),
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_config: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    impact: Mapped[str] = mapped_column(String(20), default="medium")
    time_saved_minutes: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    dismissed_at: Mapped[datetime | None] = mapped_column()
    accepted_at: Mapped[datetime | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))
