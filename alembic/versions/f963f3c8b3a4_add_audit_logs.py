"""add audit logs

Revision ID: f963f3c8b3a4
Revises: 648d963688dd
Create Date: 2026-06-07 14:03:35.854566

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f963f3c8b3a4"
down_revision: Union[str, Sequence[str], None] = "648d963688dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_id"),
        "audit_logs",
        ["id"],
        unique=False,
    )
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.BOOLEAN(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "is_active",
        existing_type=sa.BOOLEAN(),
        nullable=True,
    )
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
