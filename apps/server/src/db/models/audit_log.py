"""Audit log model for tracking command executions."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import JSONType, PortableUUID


class AuditLog(Base):
    """Audit log for tracking who executed what commands."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of action: command_executed, agent_run, setting_changed",
    )
    actor: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Who initiated: user, agent, system",
    )
    device_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("devices.id"),
    )
    command_type: Mapped[str | None] = mapped_column(String(100))
    command_params: Mapped[dict[str, Any] | None] = mapped_column(JSONType())
    result: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Result status: success, failure, pending, timeout",
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    ip_address: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    __table_args__ = (
        Index("idx_audit_logs_timestamp", "timestamp"),
        Index("idx_audit_logs_action_type", "action_type"),
        Index("idx_audit_logs_device_id", "device_id"),
        Index("idx_audit_logs_actor", "actor"),
        Index("idx_audit_logs_result", "result"),
    )
