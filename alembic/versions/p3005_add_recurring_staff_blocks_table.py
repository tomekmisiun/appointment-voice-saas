"""add recurring_staff_blocks table (P3-005)

Revision ID: p3005a2b3c4d5e
Revises: p2012a2b3c4d5e
Create Date: 2026-06-23
"""
from alembic import op
import sqlalchemy as sa

revision = "p3005a2b3c4d5e"
down_revision = "p2012a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_staff_blocks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_recurring_staff_blocks_tenant_id", "recurring_staff_blocks", ["tenant_id"]
    )
    op.create_index(
        "ix_recurring_staff_blocks_business_id", "recurring_staff_blocks", ["business_id"]
    )
    op.create_index(
        "ix_recurring_staff_blocks_staff_id", "recurring_staff_blocks", ["staff_id"]
    )
    op.create_index(
        "ix_recurring_staff_blocks_day_of_week", "recurring_staff_blocks", ["day_of_week"]
    )


def downgrade() -> None:
    op.drop_index("ix_recurring_staff_blocks_day_of_week", table_name="recurring_staff_blocks")
    op.drop_index("ix_recurring_staff_blocks_staff_id", table_name="recurring_staff_blocks")
    op.drop_index("ix_recurring_staff_blocks_business_id", table_name="recurring_staff_blocks")
    op.drop_index("ix_recurring_staff_blocks_tenant_id", table_name="recurring_staff_blocks")
    op.drop_table("recurring_staff_blocks")
