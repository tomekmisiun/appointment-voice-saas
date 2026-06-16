"""add calendar_event cancel_attempts column

Revision ID: f5e4d3c2b1a0
Revises: c2d3e4f5a6b7
Create Date: 2026-06-16 00:00:02.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f5e4d3c2b1a0"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "calendar_events",
        sa.Column(
            "cancel_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("calendar_events", "cancel_attempts")
