"""add transfer_destination to voice_sessions

Revision ID: i003a2b3c4d5
Revises: i001b2c3d4e5
Create Date: 2026-06-16 00:00:07.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i003a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "i001b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "voice_sessions",
        sa.Column("transfer_destination", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("voice_sessions", "transfer_destination")
