"""add idempotency and webhook events

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-11 18:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_key", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_key"),
    )
    op.create_index(
        op.f("ix_idempotency_records_id"),
        "idempotency_records",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_records_scope_key"),
        "idempotency_records",
        ["scope_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_idempotency_records_created_at"),
        "idempotency_records",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_records_expires_at"),
        "idempotency_records",
        ["expires_at"],
        unique=False,
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("payload_hash", sa.String(), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "event_id", name="uq_webhook_events_provider_event_id"),
    )
    op.create_index(op.f("ix_webhook_events_id"), "webhook_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_webhook_events_provider"),
        "webhook_events",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_received_at"),
        "webhook_events",
        ["received_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_webhook_events_received_at"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_provider"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_id"), table_name="webhook_events")
    op.drop_table("webhook_events")

    op.drop_index(
        op.f("ix_idempotency_records_expires_at"),
        table_name="idempotency_records",
    )
    op.drop_index(
        op.f("ix_idempotency_records_created_at"),
        table_name="idempotency_records",
    )
    op.drop_index(
        op.f("ix_idempotency_records_scope_key"),
        table_name="idempotency_records",
    )
    op.drop_index(op.f("ix_idempotency_records_id"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
