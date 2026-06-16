"""add transfer settings to businesses

Revision ID: i001a2b3c4d5
Revises: h001a2b3c4d5
Create Date: 2026-06-16 00:00:05.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "i001a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "h001a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column(
            "transfer_enabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column(
        "businesses",
        sa.Column(
            "transfer_destination_policy",
            sa.String(32),
            nullable=False,
            server_default="business_phone",
        ),
    )


def downgrade() -> None:
    op.drop_column("businesses", "transfer_destination_policy")
    op.drop_column("businesses", "transfer_enabled")
