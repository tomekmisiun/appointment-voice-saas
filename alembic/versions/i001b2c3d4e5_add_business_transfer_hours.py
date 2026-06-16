"""add business_transfer_hours table

Revision ID: i001b2c3d4e5
Revises: i001a2b3c4d5
Create Date: 2026-06-16 00:00:06.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i001b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "i001a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "business_transfer_hours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("business_id", "day_of_week", "start_time", name="uq_bth_business_day_start"),
    )
    op.create_index("ix_business_transfer_hours_tenant_id", "business_transfer_hours", ["tenant_id"])
    op.create_index("ix_business_transfer_hours_business_id", "business_transfer_hours", ["business_id"])


def downgrade() -> None:
    op.drop_index("ix_business_transfer_hours_business_id", table_name="business_transfer_hours")
    op.drop_index("ix_business_transfer_hours_tenant_id", table_name="business_transfer_hours")
    op.drop_table("business_transfer_hours")
