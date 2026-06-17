"""add invalid_key_count to voice_sessions (P1-006)

Revision ID: p1006a2b3c4d5e
Revises: p1005a2b3c4d5e
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "p1006a2b3c4d5e"
down_revision = "p1005a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_sessions",
        sa.Column(
            "invalid_key_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("voice_sessions", "invalid_key_count")
