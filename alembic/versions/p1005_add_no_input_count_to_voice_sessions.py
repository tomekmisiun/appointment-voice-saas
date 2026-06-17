"""add no_input_count to voice_sessions (P1-005)

Revision ID: p1005a2b3c4d5e
Revises: l001a2b3c4d5e
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "p1005a2b3c4d5e"
down_revision = "l001a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "voice_sessions",
        sa.Column(
            "no_input_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("voice_sessions", "no_input_count")
