"""Add automation state tables and sessions.

Revision ID: 007
Revises: 006
Create Date: 2026-01-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create automation state and session tables."""

    # Device statuses table
    op.create_table(
        "device_statuses",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connected", sa.Boolean(), default=False),
        sa.Column("status", sa.String(50), default="idle"),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("status_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_device_statuses_device_id", "device_statuses", ["device_id"])

    # Command results table
    op.create_table(
        "command_results",
        sa.Column("id", sa.String(64), primary_key=True),  # command_id
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("command_type", sa.String(100), nullable=False),
        sa.Column("command_params", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(50), default="pending"),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("result_data", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_command_results_device_id", "command_results", ["device_id"])
    op.create_index("idx_command_results_status", "command_results", ["status"])

    # Screenshots table
    op.create_table(
        "screenshots",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("command_id", sa.String(64), sa.ForeignKey("command_results.id", ondelete="SET NULL"), nullable=True),
        sa.Column("screenshot_data", sa.Text(), nullable=False),  # base64
        sa.Column("ocr_text", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_screenshots_device_id", "screenshots", ["device_id"])
    op.create_index("idx_screenshots_captured_at", "screenshots", ["captured_at"])

    # Feedbacks table
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("feedback_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=True),
        sa.Column("session_id", sa.String(64), nullable=True),
        sa.Column("message_id", sa.String(64), nullable=True),
        sa.Column("agent_id", sa.String(64), nullable=True),
        sa.Column("processed", sa.Boolean(), default=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("idx_feedbacks_type", "feedbacks", ["feedback_type"])
    op.create_index("idx_feedbacks_session_id", "feedbacks", ["session_id"])
    op.create_index("idx_feedbacks_created_at", "feedbacks", ["created_at"])

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", sa.String(64), unique=True, nullable=False),
        sa.Column("device_id", sa.String(64), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Float(), nullable=True),
        sa.Column("apps_used", postgresql.ARRAY(sa.String), default=list),
        sa.Column("events_count", sa.Integer(), default=0),
        sa.Column("productivity_score", sa.Float(), nullable=True),
        sa.Column("session_metadata", postgresql.JSONB(), default=dict),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("idx_sessions_session_id", "sessions", ["session_id"])
    op.create_index("idx_sessions_device_time", "sessions", ["device_id", "start_time"])
    op.create_index("idx_sessions_start_time", "sessions", ["start_time"])
    op.create_index("idx_sessions_end_time", "sessions", ["end_time"])


def downgrade() -> None:
    """Drop automation state and session tables."""
    # Sessions
    op.drop_index("idx_sessions_end_time", table_name="sessions")
    op.drop_index("idx_sessions_start_time", table_name="sessions")
    op.drop_index("idx_sessions_device_time", table_name="sessions")
    op.drop_index("idx_sessions_session_id", table_name="sessions")
    op.drop_table("sessions")

    # Feedbacks
    op.drop_index("idx_feedbacks_created_at", table_name="feedbacks")
    op.drop_index("idx_feedbacks_session_id", table_name="feedbacks")
    op.drop_index("idx_feedbacks_type", table_name="feedbacks")
    op.drop_table("feedbacks")

    # Screenshots
    op.drop_index("idx_screenshots_captured_at", table_name="screenshots")
    op.drop_index("idx_screenshots_device_id", table_name="screenshots")
    op.drop_table("screenshots")

    # Command results
    op.drop_index("idx_command_results_status", table_name="command_results")
    op.drop_index("idx_command_results_device_id", table_name="command_results")
    op.drop_table("command_results")

    # Device statuses
    op.drop_index("idx_device_statuses_device_id", table_name="device_statuses")
    op.drop_table("device_statuses")
