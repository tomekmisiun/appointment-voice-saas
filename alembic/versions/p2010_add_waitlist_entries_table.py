"""add waitlist_entries table (P2-010)

Revision ID: p2010a2b3c4d5e
Revises: p2008a2b3c4d5e
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "p2010a2b3c4d5e"
down_revision = "p2008a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True),
        sa.Column("desired_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="waiting"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_waitlist_entries_tenant_id", "waitlist_entries", ["tenant_id"])
    op.create_index("ix_waitlist_entries_business_id", "waitlist_entries", ["business_id"])
    op.create_index("ix_waitlist_entries_status", "waitlist_entries", ["status"])
    op.create_index(
        "ix_waitlist_entries_business_service_date",
        "waitlist_entries",
        ["business_id", "service_id", "desired_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_entries_business_service_date", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_status", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_business_id", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_tenant_id", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")
