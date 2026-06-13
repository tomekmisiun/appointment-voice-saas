"""add uploaded files

Revision ID: 9b2c4d6e8f10
Revises: 3a9f1c7d8e20
Create Date: 2026-06-10 19:15:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9b2c4d6e8f10"
down_revision: Union[str, Sequence[str], None] = "3a9f1c7d8e20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "uploaded_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("object_key", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index(
        op.f("ix_uploaded_files_id"),
        "uploaded_files",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_uploaded_files_owner_id"),
        "uploaded_files",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_uploaded_files_created_at"),
        "uploaded_files",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_uploaded_files_created_at"), table_name="uploaded_files")
    op.drop_index(op.f("ix_uploaded_files_owner_id"), table_name="uploaded_files")
    op.drop_index(op.f("ix_uploaded_files_id"), table_name="uploaded_files")
    op.drop_table("uploaded_files")
