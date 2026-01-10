"""Agent model."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import JSONType, PortableUUID


class Agent(Base):
    """Automation agent that performs tasks."""

    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_config: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)
    actions: Mapped[list[dict[str, Any]]] = mapped_column(JSONType(), nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(JSONType(), default=dict)
    code: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    last_run_at: Mapped[datetime | None] = mapped_column()
    last_error: Mapped[str | None] = mapped_column(Text)
    run_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    total_time_saved_seconds: Mapped[float] = mapped_column(Float, default=0)
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        PortableUUID(),
        ForeignKey("suggestions.id"),
    )
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )


class AgentLog(Base):
    """Log entry for agent execution."""

    __tablename__ = "agent_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSONType())
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))

    __table_args__ = (
        Index("idx_agent_logs_agent", "agent_id", "created_at"),
    )
