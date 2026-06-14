"""add appointment domain tables

Revision ID: 1a2b3c4d5e6f
Revises: b3c4d5e6f7a8
Create Date: 2026-06-14 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_businesses_tenant_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_businesses_tenant_id", "businesses", ["tenant_id"])

    op.create_table(
        "staff",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_staff_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_staff_business_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staff_tenant_id", "staff", ["tenant_id"])
    op.create_index("ix_staff_business_id", "staff", ["business_id"])

    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("price_minor_units", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_services_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_services_business_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_tenant_id", "services", ["tenant_id"])
    op.create_index("ix_services_business_id", "services", ["business_id"])

    op.create_table(
        "working_hours",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_working_hours_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_working_hours_business_id"
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"], ["staff.id"], name="fk_working_hours_staff_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_working_hours_tenant_id", "working_hours", ["tenant_id"])
    op.create_index("ix_working_hours_business_id", "working_hours", ["business_id"])
    op.create_index("ix_working_hours_staff_id", "working_hours", ["staff_id"])

    op.create_table(
        "availability_exceptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "is_closed", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("start_time", sa.Time(), nullable=True),
        sa.Column("end_time", sa.Time(), nullable=True),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_availability_exceptions_tenant_id",
        ),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["businesses.id"],
            name="fk_availability_exceptions_business_id",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff.id"],
            name="fk_availability_exceptions_staff_id",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_availability_exceptions_tenant_id",
        "availability_exceptions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_availability_exceptions_business_id",
        "availability_exceptions",
        ["business_id"],
    )
    op.create_index(
        "ix_availability_exceptions_staff_id",
        "availability_exceptions",
        ["staff_id"],
    )
    op.create_index(
        "ix_availability_exceptions_date",
        "availability_exceptions",
        ["date"],
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("phone_normalized", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_customers_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_customers_business_id"
        ),
        sa.UniqueConstraint(
            "business_id",
            "phone_normalized",
            name="uq_customers_business_phone",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])
    op.create_index("ix_customers_business_id", "customers", ["business_id"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("staff_id", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="confirmed",
        ),
        sa.Column(
            "source",
            sa.String(32),
            nullable=False,
            server_default="api",
        ),
        sa.Column("cancel_reason", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_bookings_tenant_id"
        ),
        sa.ForeignKeyConstraint(
            ["business_id"], ["businesses.id"], name="fk_bookings_business_id"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], name="fk_bookings_customer_id"
        ),
        sa.ForeignKeyConstraint(
            ["service_id"], ["services.id"], name="fk_bookings_service_id"
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"], ["staff.id"], name="fk_bookings_staff_id"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_tenant_id", "bookings", ["tenant_id"])
    op.create_index("ix_bookings_business_id", "bookings", ["business_id"])
    op.create_index("ix_bookings_customer_id", "bookings", ["customer_id"])
    op.create_index(
        "ix_bookings_staff_id_starts_at", "bookings", ["staff_id", "starts_at"]
    )


def downgrade() -> None:
    op.drop_table("bookings")
    op.drop_table("customers")
    op.drop_table("availability_exceptions")
    op.drop_table("working_hours")
    op.drop_table("services")
    op.drop_table("staff")
    op.drop_table("businesses")
