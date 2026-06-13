"""allow system audit logs

Revision ID: 4d5e6f7a8b90
Revises: 9b2c4d6e8f10
Create Date: 2026-06-10 20:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4d5e6f7a8b90"
down_revision: Union[str, Sequence[str], None] = "9b2c4d6e8f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "audit_logs",
        "admin_id",
        existing_type=sa.INTEGER(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "audit_logs",
        "admin_id",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
