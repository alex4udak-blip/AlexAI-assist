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
    op.create_index("idx_events_app_name", "events", ["app_name"], if_not_exists=True)
    op.create_index("idx_events_created_at", "events", ["created_at"], if_not_exists=True)

    # Patterns table
    op.create_index("idx_patterns_occurrences", "patterns", ["occurrences"], if_not_exists=True)

    # Sessions table
    op.create_index("idx_sessions_end_time", "sessions", ["end_time"], if_not_exists=True)

    # Agents table
    op.create_index("idx_agents_status", "agents", ["status"], if_not_exists=True)

    # Suggestions table
    op.create_index("idx_suggestions_status", "suggestions", ["status"], if_not_exists=True)

    # Chat messages composite index
    op.create_index(
        "idx_chat_messages_session_timestamp",
        "chat_messages",
        ["session_id", "timestamp"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_chat_messages_session_timestamp", table_name="chat_messages", if_exists=True)
    op.drop_index("idx_suggestions_status", table_name="suggestions", if_exists=True)
    op.drop_index("idx_agents_status", table_name="agents", if_exists=True)
    op.drop_index("idx_sessions_end_time", table_name="sessions", if_exists=True)
    op.drop_index("idx_patterns_occurrences", table_name="patterns", if_exists=True)
    op.drop_index("idx_events_created_at", table_name="events", if_exists=True)
    op.drop_index("idx_events_app_name", table_name="events", if_exists=True)
