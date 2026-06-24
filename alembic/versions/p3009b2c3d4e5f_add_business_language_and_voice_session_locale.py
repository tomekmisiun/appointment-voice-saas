"""add Business.language and VoiceSession.locale for per-business IVR
locale (P3-009 follow-up)

Revision ID: p3009b2c3d4e5f
Revises: p3010a2b3c4d5e
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "p3009b2c3d4e5f"
down_revision = "p3010a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("language", sa.String(length=8), nullable=False, server_default="en"),
    )
    op.add_column(
        "voice_sessions",
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="en"),
    )


def downgrade() -> None:
    op.drop_column("voice_sessions", "locale")
    op.drop_column("businesses", "language")
