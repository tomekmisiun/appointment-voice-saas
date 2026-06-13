"""add audit log query indexes

Revision ID: 7f4e8b9a2c10
Revises: f963f3c8b3a4
Create Date: 2026-06-10 13:55:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "7f4e8b9a2c10"
down_revision: Union[str, Sequence[str], None] = "f963f3c8b3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_audit_logs_action"),
        "audit_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_admin_id"),
        "audit_logs",
        ["admin_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_target_user_id"),
        "audit_logs",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_created_at"),
        "audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_admin_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
