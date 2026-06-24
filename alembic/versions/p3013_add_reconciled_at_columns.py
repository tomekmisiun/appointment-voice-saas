"""add reconciled_at columns to notification_outbox and calendar_events (P3-013)

Revision ID: p3013a2b3c4d5e
Revises: p3005a2b3c4d5e
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "p3013a2b3c4d5e"
down_revision = "p3005a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_outbox",
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "calendar_events",
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("calendar_events", "reconciled_at")
    op.drop_column("notification_outbox", "reconciled_at")
