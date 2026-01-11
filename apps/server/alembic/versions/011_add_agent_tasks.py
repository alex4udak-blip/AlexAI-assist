"""Add agent_tasks table for task queue.

Revision ID: 011
Revises: 010
Create Date: 2026-01-11

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: str = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("project_path", sa.String(1024)),
        sa.Column("priority", sa.String(20), server_default=sa.text("'normal'")),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("result", sa.Text),
        sa.Column("error", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_agent_tasks_status", "agent_tasks", ["status"])
    op.create_index("idx_agent_tasks_priority", "agent_tasks", ["priority"])
    op.create_index("idx_agent_tasks_created_at", "agent_tasks", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_agent_tasks_created_at", table_name="agent_tasks")
    op.drop_index("idx_agent_tasks_priority", table_name="agent_tasks")
    op.drop_index("idx_agent_tasks_status", table_name="agent_tasks")
    op.drop_table("agent_tasks")
