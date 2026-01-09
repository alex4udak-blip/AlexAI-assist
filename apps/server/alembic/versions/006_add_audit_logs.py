"""Add audit_logs table.

Revision ID: 006
Revises: 005
Create Date: 2026-01-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create audit_logs table."""
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False, comment="Type of action: command_executed, agent_run, setting_changed"),
        sa.Column("actor", sa.String(50), nullable=False, comment="Who initiated: user, agent, system"),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=True),
        sa.Column("command_type", sa.String(100), nullable=True),
        sa.Column("command_params", postgresql.JSONB(), nullable=True),
        sa.Column("result", sa.String(20), nullable=False, comment="Result status: success, failure, pending, timeout"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("idx_audit_logs_action_type", "audit_logs", ["action_type"])
    op.create_index("idx_audit_logs_device_id", "audit_logs", ["device_id"])
    op.create_index("idx_audit_logs_actor", "audit_logs", ["actor"])
    op.create_index("idx_audit_logs_result", "audit_logs", ["result"])


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_index("idx_audit_logs_result", table_name="audit_logs")
    op.drop_index("idx_audit_logs_actor", table_name="audit_logs")
    op.drop_index("idx_audit_logs_device_id", table_name="audit_logs")
    op.drop_index("idx_audit_logs_action_type", table_name="audit_logs")
    op.drop_index("idx_audit_logs_timestamp", table_name="audit_logs")
    op.drop_table("audit_logs")
