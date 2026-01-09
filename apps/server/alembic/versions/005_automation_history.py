"""
Add automation_commands and agent_suggestions tables

Revision ID: 005
Revises: 004
Create Date: 2026-01-09
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add automation_commands and agent_suggestions tables."""

    # Create automation_commands table
    op.create_table(
        "automation_commands",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("command_type", sa.String(100), nullable=False),
        sa.Column("params", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", JSONB, nullable=True),
        sa.Column("success", sa.Boolean, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("screenshot_url", sa.String(500), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("requires_confirmation", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("confirmed_by_user", sa.Boolean, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(NOW() AT TIME ZONE 'utc')")),
    )

    # Create indexes for automation_commands
    op.create_index(
        "idx_automation_commands_device",
        "automation_commands",
        ["device_id"],
    )
    op.create_index(
        "idx_automation_commands_agent",
        "automation_commands",
        ["agent_id"],
    )
    op.create_index(
        "idx_automation_commands_created",
        "automation_commands",
        ["created_at"],
    )
    op.create_index(
        "idx_automation_commands_type",
        "automation_commands",
        ["command_type"],
    )

    # Create agent_suggestions table
    op.create_table(
        "agent_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("pattern_type", sa.String(50), nullable=False),
        sa.Column("pattern_data", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("suggestion", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("(NOW() AT TIME ZONE 'utc')")),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
    )

    # Create indexes for agent_suggestions
    op.create_index(
        "idx_agent_suggestions_user",
        "agent_suggestions",
        ["user_id"],
    )
    op.create_index(
        "idx_agent_suggestions_status",
        "agent_suggestions",
        ["status"],
    )
    op.create_index(
        "idx_agent_suggestions_created",
        "agent_suggestions",
        ["created_at"],
    )
    op.create_index(
        "idx_agent_suggestions_pattern_type",
        "agent_suggestions",
        ["pattern_type"],
    )


def downgrade() -> None:
    """Remove automation_commands and agent_suggestions tables."""

    # Drop indexes first
    op.drop_index("idx_agent_suggestions_pattern_type", table_name="agent_suggestions")
    op.drop_index("idx_agent_suggestions_created", table_name="agent_suggestions")
    op.drop_index("idx_agent_suggestions_status", table_name="agent_suggestions")
    op.drop_index("idx_agent_suggestions_user", table_name="agent_suggestions")

    op.drop_index("idx_automation_commands_type", table_name="automation_commands")
    op.drop_index("idx_automation_commands_created", table_name="automation_commands")
    op.drop_index("idx_automation_commands_agent", table_name="automation_commands")
    op.drop_index("idx_automation_commands_device", table_name="automation_commands")

    # Drop tables
    op.drop_table("agent_suggestions")
    op.drop_table("automation_commands")
