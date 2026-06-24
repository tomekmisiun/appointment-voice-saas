"""add deposits/payment-holds: Service deposit fields, booking_payments
table, widen no_overlapping_staff_bookings to PENDING_PAYMENT (P3-008, ADR
0004)

Revision ID: p3008a2b3c4d5e
Revises: p3013a2b3c4d5e
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "p3008a2b3c4d5e"
down_revision = "p3013a2b3c4d5e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "services",
        sa.Column(
            "deposit_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "services",
        sa.Column("deposit_minor_units", sa.Integer(), nullable=True),
    )

    op.create_table(
        "booking_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("business_id", sa.Integer(), sa.ForeignKey("businesses.id"), nullable=False),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("bookings.id"), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_session_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_id", sa.String(length=255), nullable=True),
        sa.Column("amount_minor_units", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("failure_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("booking_id", name="uq_booking_payments_booking_id"),
    )
    op.create_index(
        "ix_booking_payments_tenant_id", "booking_payments", ["tenant_id"]
    )
    op.create_index(
        "ix_booking_payments_business_id", "booking_payments", ["business_id"]
    )
    op.create_index("ix_booking_payments_status", "booking_payments", ["status"])

    op.execute(
        "ALTER TABLE bookings DROP CONSTRAINT no_overlapping_staff_bookings"
    )
    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT no_overlapping_staff_bookings
        EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status IN ('confirmed', 'pending_payment') AND staff_id IS NOT NULL)
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE bookings DROP CONSTRAINT no_overlapping_staff_bookings"
    )
    op.execute(
        """
        ALTER TABLE bookings
        ADD CONSTRAINT no_overlapping_staff_bookings
        EXCLUDE USING gist (
            staff_id WITH =,
            tstzrange(starts_at, ends_at, '[)') WITH &&
        )
        WHERE (status = 'confirmed' AND staff_id IS NOT NULL)
        """
    )

    op.drop_index("ix_booking_payments_status", table_name="booking_payments")
    op.drop_index("ix_booking_payments_business_id", table_name="booking_payments")
    op.drop_index("ix_booking_payments_tenant_id", table_name="booking_payments")
    op.drop_table("booking_payments")

    op.drop_column("services", "deposit_minor_units")
    op.drop_column("services", "deposit_required")
