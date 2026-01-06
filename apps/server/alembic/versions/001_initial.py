"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("os", sa.String(50), nullable=False),
        sa.Column("os_version", sa.String(50)),
        sa.Column("app_version", sa.String(50)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Events table
    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "device_id",
            sa.String(64),
            sa.ForeignKey("devices.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("app_name", sa.String(255)),
        sa.Column("window_title", sa.Text),
        sa.Column("url", sa.Text),
        sa.Column(
            "data",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("category", sa.String(50)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_events_device_time", "events", ["device_id", "timestamp"])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_category", "events", ["category"])

    # Patterns table
    op.create_table(
        "patterns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("trigger_conditions", postgresql.JSONB, nullable=False),
        sa.Column("sequence", postgresql.JSONB, nullable=False),
        sa.Column("occurrences", sa.Integer, server_default=sa.text("0")),
        sa.Column("avg_duration_seconds", sa.Float),
        sa.Column("first_seen_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("automatable", sa.Boolean, server_default=sa.text("false")),
        sa.Column("complexity", sa.String(20), server_default=sa.text("'medium'")),
        sa.Column("time_saved_minutes", sa.Float, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Suggestions table
    op.create_table(
        "suggestions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column(
            "pattern_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("patterns.id"),
        ),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("agent_config", postgresql.JSONB, nullable=False),
        sa.Column("confidence", sa.Float, server_default=sa.text("0")),
        sa.Column("impact", sa.String(20), server_default=sa.text("'medium'")),
        sa.Column("time_saved_minutes", sa.Float, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("dismissed_at", sa.DateTime(timezone=True)),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Agents table
    op.create_table(
        "agents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB, nullable=False),
        sa.Column("actions", postgresql.JSONB, nullable=False),
        sa.Column(
            "settings",
            postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("code", sa.Text),
        sa.Column("status", sa.String(20), server_default=sa.text("'draft'")),
        sa.Column("last_run_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("run_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("success_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("error_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("total_time_saved_seconds", sa.Float, server_default=sa.text("0")),
        sa.Column(
            "suggestion_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("suggestions.id"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )

    # Agent logs table
    op.create_table(
        "agent_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("data", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("idx_agent_logs_agent", "agent_logs", ["agent_id", "created_at"])


def downgrade() -> None:
    op.drop_table("agent_logs")
    op.drop_table("agents")
    op.drop_table("suggestions")
    op.drop_table("patterns")
    op.drop_table("events")
    op.drop_table("devices")
