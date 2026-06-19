"""add waitlist_entries.offered_for_staff_id (P2-012)

Revision ID: p2012a2b3c4d5e
Revises: p2010a2b3c4d5e
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "p2012a2b3c4d5e"
down_revision = "p2010a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "waitlist_entries",
        sa.Column(
            "offered_for_staff_id",
            sa.Integer(),
            sa.ForeignKey("staff.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("waitlist_entries", "offered_for_staff_id")
