"""add managed_booking_id to voice_sessions (P1-003)

Revision ID: p1003a2b3c4d5e
Revises: p1006a2b3c4d5e
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "p1003a2b3c4d5e"
down_revision = "p1006a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_sessions",
        sa.Column(
            "managed_booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("voice_sessions", "managed_booking_id")
