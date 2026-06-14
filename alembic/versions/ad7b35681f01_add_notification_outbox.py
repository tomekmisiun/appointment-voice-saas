"""add notification outbox

Revision ID: ad7b35681f01
Revises: 32e2a5c45a2d
Create Date: 2026-06-14 18:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "ad7b35681f01"
down_revision: Union[str, Sequence[str], None] = "32e2a5c45a2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("recipient_phone", sa.String(32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_notification_outbox_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_notification_outbox_business_id"
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"], ["bookings.id"], name="fk_notification_outbox_booking_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notification_outbox_tenant_id", "notification_outbox", ["tenant_id"]
    )
    op.create_index(
        "ix_notification_outbox_business_id", "notification_outbox", ["business_id"]
    )
    op.create_index(
        "ix_notification_outbox_booking_id", "notification_outbox", ["booking_id"]
    )
    op.create_index(
        "ix_notification_outbox_status", "notification_outbox", ["status"]
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_booking_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_business_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_tenant_id", table_name="notification_outbox")
    op.drop_table("notification_outbox")
