"""add twilio tracking fields: call_sid and provider_message_id

Revision ID: h001a2b3c4d5
Revises: g001a2b3c4d5
Create Date: 2026-06-16 00:00:04.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "h001a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "g001a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_sessions",
        sa.Column("call_sid", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_voice_sessions_call_sid",
        "voice_sessions",
        ["call_sid"],
        unique=True,
        postgresql_where=sa.text("call_sid IS NOT NULL"),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("provider_message_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_notification_outbox_provider_message_id",
        "notification_outbox",
        ["provider_message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_provider_message_id", "notification_outbox")
    op.drop_column("notification_outbox", "provider_message_id")
    op.drop_index("ix_voice_sessions_call_sid", "voice_sessions")
    op.drop_column("voice_sessions", "call_sid")
