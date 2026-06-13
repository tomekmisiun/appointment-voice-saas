"""add password reset job completions

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-13 09:35:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_job_completions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        op.f("ix_password_reset_job_completions_id"),
        "password_reset_job_completions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_reset_job_completions_job_id"),
        "password_reset_job_completions",
        ["job_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_password_reset_job_completions_job_id"),
        table_name="password_reset_job_completions",
    )
    op.drop_index(
        op.f("ix_password_reset_job_completions_id"),
        table_name="password_reset_job_completions",
    )
    op.drop_table("password_reset_job_completions")
