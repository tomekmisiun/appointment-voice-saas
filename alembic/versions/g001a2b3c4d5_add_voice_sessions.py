"""add voice_sessions table

Revision ID: g001a2b3c4d5
Revises: f5e4d3c2b1a0
Create Date: 2026-06-16 00:00:03.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "g001a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "f5e4d3c2b1a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("caller_phone", sa.String(32), nullable=False),
        sa.Column("step", sa.String(32), nullable=False),
        sa.Column("selected_service_id", sa.Integer(), nullable=True),
        sa.Column("selected_staff_id", sa.Integer(), nullable=True),
        sa.Column("selected_slot_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_slot_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("slot_candidates", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["selected_service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["selected_staff_id"], ["staff.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_sessions_tenant_id", "voice_sessions", ["tenant_id"])
    op.create_index("ix_voice_sessions_business_id", "voice_sessions", ["business_id"])
    op.create_index("ix_voice_sessions_step", "voice_sessions", ["step"])
    op.create_index("ix_voice_sessions_expires_at", "voice_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_voice_sessions_expires_at", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_step", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_business_id", table_name="voice_sessions")
    op.drop_index("ix_voice_sessions_tenant_id", table_name="voice_sessions")
    op.drop_table("voice_sessions")
