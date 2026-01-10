"""Add performance indexes for frequently queried columns.

Revision ID: 010
Revises: 009
Create Date: 2026-01-10

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: str = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Events table
    op.create_index("idx_events_app_name", "events", ["app_name"])
    op.create_index("idx_events_created_at", "events", ["created_at"])

    # Patterns table
    op.create_index("idx_patterns_occurrences", "patterns", ["occurrences"])

    # Sessions table
    op.create_index("idx_sessions_end_time", "sessions", ["end_time"])

    # Agents table
    op.create_index("idx_agents_status", "agents", ["status"])

    # Suggestions table
    op.create_index("idx_suggestions_status", "suggestions", ["status"])

    # Chat messages composite index
    op.create_index(
        "idx_chat_messages_session_timestamp",
        "chat_messages",
        ["session_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("idx_chat_messages_session_timestamp", table_name="chat_messages")
    op.drop_index("idx_suggestions_status", table_name="suggestions")
    op.drop_index("idx_agents_status", table_name="agents")
    op.drop_index("idx_sessions_end_time", table_name="sessions")
    op.drop_index("idx_patterns_occurrences", table_name="patterns")
    op.drop_index("idx_events_created_at", table_name="events")
    op.drop_index("idx_events_app_name", table_name="events")
