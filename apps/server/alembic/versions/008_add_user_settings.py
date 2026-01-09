"""Add user settings table.

Revision ID: 008
Revises: 007
Create Date: 2026-01-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user settings table."""

    op.create_table(
        "user_settings",
        sa.Column("device_id", sa.String(255), primary_key=True),
        sa.Column("settings", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    """Drop user settings table."""
    op.drop_table("user_settings")
