"""Chat message model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.types import PortableUUID


class ChatMessage(Base):
    """Chat message stored in database."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PortableUUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, default="default")
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC).replace(tzinfo=None))

    __table_args__ = (
        Index("idx_chat_session", "session_id"),
        Index("idx_chat_timestamp", "timestamp"),
    )
