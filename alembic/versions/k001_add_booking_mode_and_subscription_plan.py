"""add booking_mode and subscription_plan to businesses

Revision ID: k001a2b3c4d5e
Revises: i003a2b3c4d5
Create Date: 2026-06-16

Adds two independent dimensions to the businesses table:
  booking_mode      — operational: who owns the booking flow (internal vs external link)
  subscription_plan — commercial: what features/limits the plan includes

All existing businesses default to internal_booking / full_booking via server_default.
"""
from alembic import op
import sqlalchemy as sa

revision = "k001a2b3c4d5e"
down_revision = "i003a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("booking_mode", sa.String(32), nullable=False,
                  server_default="internal_booking"),
    )
    op.add_column(
        "businesses",
        sa.Column("external_booking_url", sa.String(512), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("external_booking_label", sa.String(128), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("external_booking_provider", sa.String(32), nullable=True),
    )
    op.add_column(
        "businesses",
        sa.Column("subscription_plan", sa.String(32), nullable=False,
                  server_default="full_booking"),
    )


def downgrade() -> None:
    for col in (
        "subscription_plan",
        "external_booking_provider",
        "external_booking_label",
        "external_booking_url",
        "booking_mode",
    ):
        op.drop_column("businesses", col)
