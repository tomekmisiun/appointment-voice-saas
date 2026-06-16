"""add calendar integrations

Revision ID: b1c2d3e4f5a6
Revises: ad7b35681f01
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "ad7b35681f01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "calendar_integrations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("calendar_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["staff_id"], ["staff.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calendar_integrations_tenant_id",
        "calendar_integrations",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "uix_calendar_integrations_business_level",
        "calendar_integrations",
        ["business_id"],
        unique=True,
        postgresql_where=sa.text("staff_id IS NULL"),
    )
    op.create_index(
        "uix_calendar_integrations_staff_level",
        "calendar_integrations",
        ["business_id", "staff_id"],
        unique=True,
        postgresql_where=sa.text("staff_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uix_calendar_integrations_staff_level", table_name="calendar_integrations")
    op.drop_index("uix_calendar_integrations_business_level", table_name="calendar_integrations")
    op.drop_index("ix_calendar_integrations_tenant_id", table_name="calendar_integrations")
    op.drop_table("calendar_integrations")
