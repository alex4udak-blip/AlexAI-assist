"""Add chat messages table.

Revision ID: 002
Revises: 001
Create Date: 2024-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create chat_messages table."""
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False, server_default="default"),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_chat_session", "chat_messages", ["session_id"])
    op.create_index("idx_chat_timestamp", "chat_messages", ["timestamp"])


def downgrade() -> None:
    """Drop chat_messages table."""
    op.drop_index("idx_chat_timestamp", table_name="chat_messages")
    op.drop_index("idx_chat_session", table_name="chat_messages")
    op.drop_table("chat_messages")
