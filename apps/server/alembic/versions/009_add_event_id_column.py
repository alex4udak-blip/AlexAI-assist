"""Add event_id column to events table

Revision ID: 009
Revises: 008
Create Date: 2026-01-09

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: str = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add event_id column to events table
    op.add_column(
        "events",
        sa.Column("event_id", sa.String(255), nullable=True),
    )

    # Create unique index for event_id
    op.create_index(
        "idx_events_event_id",
        "events",
        ["event_id"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_events_event_id", table_name="events")
    op.drop_column("events", "event_id")
