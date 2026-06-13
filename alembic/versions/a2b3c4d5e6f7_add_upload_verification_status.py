"""add uploaded file verification status

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-06-13 15:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "uploaded_files",
        sa.Column(
            "verification_status",
            sa.String(),
            nullable=False,
            server_default="verified",
        ),
    )


def downgrade() -> None:
    op.drop_column("uploaded_files", "verification_status")
