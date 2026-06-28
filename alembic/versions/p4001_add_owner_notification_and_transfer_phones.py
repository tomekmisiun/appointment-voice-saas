"""add owner_notification_phone and transfer_phone_number to businesses

Revision ID: p4001a2b3c4d5e
Revises: demo_user_flag_a1b2c3d4
Create Date: 2026-06-28
"""
from alembic import op
import sqlalchemy as sa

revision = "p4001a2b3c4d5e"
down_revision = "demo_user_flag_a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("owner_notification_phone", sa.String(32), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("transfer_phone_number", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("businesses", "transfer_phone_number")
    op.drop_column("businesses", "owner_notification_phone")
