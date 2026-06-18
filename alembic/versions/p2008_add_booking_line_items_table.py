"""add booking_line_items table (P2-008)

Revision ID: p2008a2b3c4d5e
Revises: p2001a2b3c4d5e
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "p2008a2b3c4d5e"
down_revision = "p2001a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_line_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("booking_id", "position", name="uq_booking_line_items_booking_position"),
    )
    op.create_index("ix_booking_line_items_tenant_id", "booking_line_items", ["tenant_id"])
    op.create_index("ix_booking_line_items_business_id", "booking_line_items", ["business_id"])
    op.create_index("ix_booking_line_items_booking_id", "booking_line_items", ["booking_id"])


def downgrade() -> None:
    op.drop_index("ix_booking_line_items_booking_id", table_name="booking_line_items")
    op.drop_index("ix_booking_line_items_business_id", table_name="booking_line_items")
    op.drop_index("ix_booking_line_items_tenant_id", table_name="booking_line_items")
    op.drop_table("booking_line_items")
