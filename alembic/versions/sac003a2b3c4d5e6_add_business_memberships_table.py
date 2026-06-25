"""add business_memberships table (SAC-003)

Revision ID: sac003a2b3c4d5e6
Revises: p3009b2c3d4e5f
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = "sac003a2b3c4d5e6"
down_revision = "p3009b2c3d4e5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite-FK targets so business_memberships can enforce, at the DB
    # level, that a membership's business/user/staff belongs to the same
    # tenant/business the membership row claims.
    op.create_index(
        "uix_businesses_tenant_id_id", "businesses", ["tenant_id", "id"], unique=True
    )
    op.create_index(
        "uix_users_tenant_id_id", "users", ["tenant_id", "id"], unique=True
    )
    op.create_index(
        "uix_staff_business_id_id", "staff", ["business_id", "id"], unique=True
    )

    op.create_table(
        "business_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="active"),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invited_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role != 'staff' OR staff_id IS NOT NULL",
            name="ck_business_memberships_staff_role_requires_staff_id",
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'staff')",
            name="ck_business_memberships_role_valid",
        ),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'suspended', 'revoked')",
            name="ck_business_memberships_status_valid",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "business_id"],
            ["businesses.tenant_id", "businesses.id"],
            name="fk_business_memberships_business_same_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_user_same_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["business_id", "staff_id"],
            ["staff.business_id", "staff.id"],
            name="fk_business_memberships_staff_same_business",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "invited_by_user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_invited_by_same_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "revoked_by_user_id"],
            ["users.tenant_id", "users.id"],
            name="fk_business_memberships_revoked_by_same_tenant",
        ),
    )
    op.create_index(
        "uix_business_memberships_business_user",
        "business_memberships",
        ["business_id", "user_id"],
        unique=True,
    )
    op.create_index(
        "uix_business_memberships_business_staff_active",
        "business_memberships",
        ["business_id", "staff_id"],
        unique=True,
        postgresql_where=sa.text("staff_id IS NOT NULL AND status = 'active'"),
    )
    op.create_index(
        "ix_business_memberships_tenant_business_status",
        "business_memberships",
        ["tenant_id", "business_id", "status"],
    )
    op.create_index(
        "ix_business_memberships_user_id", "business_memberships", ["user_id"]
    )
    op.create_index(
        "ix_business_memberships_staff_id", "business_memberships", ["staff_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_business_memberships_staff_id", table_name="business_memberships")
    op.drop_index("ix_business_memberships_user_id", table_name="business_memberships")
    op.drop_index(
        "ix_business_memberships_tenant_business_status", table_name="business_memberships"
    )
    op.drop_index(
        "uix_business_memberships_business_staff_active", table_name="business_memberships"
    )
    op.drop_index(
        "uix_business_memberships_business_user", table_name="business_memberships"
    )
    op.drop_table("business_memberships")

    op.drop_index("uix_staff_business_id_id", table_name="staff")
    op.drop_index("uix_users_tenant_id_id", table_name="users")
    op.drop_index("uix_businesses_tenant_id_id", table_name="businesses")
