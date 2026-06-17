"""add owner_leads table for pilot lead intake

Revision ID: l001a2b3c4d5e
Revises: k001a2b3c4d5e
Create Date: 2026-06-17

Stores pre-signup pilot interest leads submitted via the public intake endpoint.
Not tenant-scoped — these are prospective new tenants, not existing ones.
"""
from alembic import op
import sqlalchemy as sa

revision = "l001a2b3c4d5e"
down_revision = "k001a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "owner_leads",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("business_name", sa.String(255), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("phone_normalized", sa.String(32), nullable=False),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("booking_mode_interest", sa.String(32), nullable=False),
        sa.Column("external_booking_url", sa.String(512), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_owner_leads_status", "owner_leads", ["status"])
    op.create_index("ix_owner_leads_created_at", "owner_leads", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_owner_leads_created_at", table_name="owner_leads")
    op.drop_index("ix_owner_leads_status", table_name="owner_leads")
    op.drop_table("owner_leads")
