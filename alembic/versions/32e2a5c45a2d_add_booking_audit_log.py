"""add target_booking_id to audit_logs for booking lifecycle audit trail

Revision ID: 32e2a5c45a2d
Revises: 2b3c4d5e6f7a
Create Date: 2026-06-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "32e2a5c45a2d"
down_revision: Union[str, Sequence[str], None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audit_logs",
        sa.Column(
            "target_booking_id",
            sa.Integer(),
            sa.ForeignKey("bookings.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "audit_logs",
        sa.Column("source", sa.String(), nullable=True),
    )
    op.create_index(
        "ix_audit_logs_target_booking_id",
        "audit_logs",
        ["target_booking_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target_booking_id", table_name="audit_logs")
    op.drop_column("audit_logs", "source")
    op.drop_column("audit_logs", "target_booking_id")
