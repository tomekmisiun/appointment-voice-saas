"""drop redundant indexes

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-06-13 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_idempotency_records_id"), table_name="idempotency_records")
    op.drop_index(
        op.f("ix_idempotency_records_scope_key"),
        table_name="idempotency_records",
    )
    op.drop_index(
        op.f("ix_idempotency_records_created_at"),
        table_name="idempotency_records",
    )
    op.drop_index(op.f("ix_webhook_events_id"), table_name="webhook_events")
    op.drop_index(op.f("ix_webhook_events_provider"), table_name="webhook_events")
    op.drop_index(op.f("ix_uploaded_files_id"), table_name="uploaded_files")
    op.drop_index(op.f("ix_uploaded_files_owner_id"), table_name="uploaded_files")
    op.drop_index(op.f("ix_uploaded_files_created_at"), table_name="uploaded_files")
    op.drop_index(op.f("ix_password_reset_tokens_id"), table_name="password_reset_tokens")
    op.drop_index(
        op.f("ix_password_reset_job_completions_id"),
        table_name="password_reset_job_completions",
    )
    op.drop_index(
        op.f("ix_password_reset_job_completions_job_id"),
        table_name="password_reset_job_completions",
    )


def downgrade() -> None:
    op.create_index(
        op.f("ix_password_reset_job_completions_job_id"),
        "password_reset_job_completions",
        ["job_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_password_reset_job_completions_id"),
        "password_reset_job_completions",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_password_reset_tokens_id"),
        "password_reset_tokens",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_uploaded_files_created_at"),
        "uploaded_files",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_uploaded_files_owner_id"),
        "uploaded_files",
        ["owner_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_uploaded_files_id"),
        "uploaded_files",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_webhook_events_provider"),
        "webhook_events",
        ["provider"],
        unique=False,
    )
    op.create_index(op.f("ix_webhook_events_id"), "webhook_events", ["id"], unique=False)
    op.create_index(
        op.f("ix_idempotency_records_created_at"),
        "idempotency_records",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_idempotency_records_scope_key"),
        "idempotency_records",
        ["scope_key"],
        unique=True,
    )
    op.create_index(
        op.f("ix_idempotency_records_id"),
        "idempotency_records",
        ["id"],
        unique=False,
    )
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_audit_logs_id"), "audit_logs", ["id"], unique=False)
