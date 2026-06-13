"""add multi-tenancy foundation

Revision ID: a1b2c3d4e5f6
Revises: 4d5e6f7a8b90
Create Date: 2026-06-11 18:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "4d5e6f7a8b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), sa.Identity(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_tenants_id"), "tenants", ["id"], unique=False)
    op.create_index(op.f("ix_tenants_slug"), "tenants", ["slug"], unique=True)

    op.execute(
        sa.text(
            "INSERT INTO tenants (slug, name, is_active) "
            "SELECT 'default', 'Default Tenant', true "
            "WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE slug = 'default')"
        )
    )

    op.add_column(
        "users",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE users SET tenant_id = "
            "(SELECT id FROM tenants WHERE slug = 'default') "
            "WHERE tenant_id IS NULL"
        )
    )
    op.alter_column("users", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_users_tenant_id_tenants",
        "users",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_index(
        "ix_users_tenant_id_email",
        "users",
        ["tenant_id", "email"],
        unique=True,
    )

    op.add_column(
        "audit_logs",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE audit_logs SET tenant_id = "
            "(SELECT id FROM tenants WHERE slug = 'default') "
            "WHERE tenant_id IS NULL"
        )
    )
    op.alter_column("audit_logs", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_audit_logs_tenant_id_tenants",
        "audit_logs",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_audit_logs_tenant_id"),
        "audit_logs",
        ["tenant_id"],
        unique=False,
    )

    op.add_column(
        "uploaded_files",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        UPDATE uploaded_files
        SET tenant_id = users.tenant_id
        FROM users
        WHERE uploaded_files.owner_id = users.id
        """
    )
    op.execute(
        sa.text(
            "UPDATE uploaded_files SET tenant_id = "
            "(SELECT id FROM tenants WHERE slug = 'default') "
            "WHERE tenant_id IS NULL"
        )
    )
    op.alter_column("uploaded_files", "tenant_id", nullable=False)
    op.create_foreign_key(
        "fk_uploaded_files_tenant_id_tenants",
        "uploaded_files",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_uploaded_files_tenant_id"),
        "uploaded_files",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_uploaded_files_tenant_id"), table_name="uploaded_files")
    op.drop_constraint(
        "fk_uploaded_files_tenant_id_tenants",
        "uploaded_files",
        type_="foreignkey",
    )
    op.drop_column("uploaded_files", "tenant_id")

    op.drop_index(op.f("ix_audit_logs_tenant_id"), table_name="audit_logs")
    op.drop_constraint(
        "fk_audit_logs_tenant_id_tenants",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_column("audit_logs", "tenant_id")

    op.drop_index("ix_users_tenant_id_email", table_name="users")
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.drop_index(op.f("ix_users_tenant_id"), table_name="users")
    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")

    op.drop_index(op.f("ix_tenants_slug"), table_name="tenants")
    op.drop_index(op.f("ix_tenants_id"), table_name="tenants")
    op.drop_table("tenants")
