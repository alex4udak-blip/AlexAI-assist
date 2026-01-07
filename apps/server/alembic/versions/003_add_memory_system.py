"""Add memory system tables.

Revision ID: 003
Revises: 002
Create Date: 2024-01-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create memory system tables."""
    # User memory - long-term facts about the user
    op.create_table(
        "user_memory",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0"),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("last_referenced", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_user_memory_session", "user_memory", ["session_id"])
    op.create_index(
        "idx_user_memory_session_category", "user_memory", ["session_id", "category"]
    )
    op.create_index("idx_user_memory_key", "user_memory", ["session_id", "key"])

    # Memory summaries - periodic summaries
    op.create_table(
        "memory_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("key_events", postgresql.JSONB(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_memory_summary_session", "memory_summaries", ["session_id"])
    op.create_index(
        "idx_memory_summary_period",
        "memory_summaries",
        ["session_id", "period_type", "period_start"],
    )

    # Memory insights - AI-generated insights
    op.create_table(
        "memory_insights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("insight_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("applied", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_memory_insights_session", "memory_insights", ["session_id"])

    # Agent knowledge - what agents have learned
    op.create_table(
        "agent_knowledge",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("knowledge_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("occurrences", sa.Integer(), server_default="1"),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index(
        "idx_agent_knowledge_agent", "agent_knowledge", ["agent_id", "knowledge_type"]
    )


def downgrade() -> None:
    """Drop memory system tables."""
    # Agent knowledge
    op.drop_index("idx_agent_knowledge_agent", table_name="agent_knowledge")
    op.drop_table("agent_knowledge")

    # Memory insights
    op.drop_index("idx_memory_insights_session", table_name="memory_insights")
    op.drop_table("memory_insights")

    # Memory summaries
    op.drop_index("idx_memory_summary_period", table_name="memory_summaries")
    op.drop_index("idx_memory_summary_session", table_name="memory_summaries")
    op.drop_table("memory_summaries")

    # User memory
    op.drop_index("idx_user_memory_key", table_name="user_memory")
    op.drop_index("idx_user_memory_session_category", table_name="user_memory")
    op.drop_index("idx_user_memory_session", table_name="user_memory")
    op.drop_table("user_memory")
