"""
Add agent_created column to patterns table

Revision ID: 004
Revises: 003
Create Date: 2026-01-09
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add agent_created column to patterns table."""
    op.add_column(
        "patterns",
        sa.Column("agent_created", sa.Boolean, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Remove agent_created column from patterns table."""
    op.drop_column("patterns", "agent_created")
