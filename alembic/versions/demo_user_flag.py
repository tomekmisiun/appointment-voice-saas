"""add is_demo_user flag to users

Revision ID: demo_user_flag_a1b2c3d4
Revises: sac009_staff_inv
Create Date: 2026-06-26
"""
from alembic import op
import sqlalchemy as sa

revision = "demo_user_flag_a1b2c3d4"
down_revision = "sac009_staff_inv"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_demo_user",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_demo_user")
