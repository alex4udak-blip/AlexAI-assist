"""Pattern model."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import JSONType, PortableUUID


class Pattern(Base):
    """Detected behavior pattern."""

    __tablename__ = "patterns"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pattern_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_conditions: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)
    sequence: Mapped[list[dict[str, Any]]] = mapped_column(JSONType(), nullable=False)
    occurrences: Mapped[int] = mapped_column(Integer, default=0)
    avg_duration_seconds: Mapped[float | None] = mapped_column(Float)
    first_seen_at: Mapped[datetime | None] = mapped_column()
    last_seen_at: Mapped[datetime | None] = mapped_column()
    automatable: Mapped[bool] = mapped_column(default=False)
    agent_created: Mapped[bool] = mapped_column(default=False)
    complexity: Mapped[str] = mapped_column(String(20), default="medium")
    time_saved_minutes: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
