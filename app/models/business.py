from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class TransferDestinationPolicy(StrEnum):
    BUSINESS_PHONE = "business_phone"
    STAFF = "staff"


class BookingMode(StrEnum):
    INTERNAL_BOOKING      = "internal_booking"
    EXTERNAL_BOOKING_LINK = "external_booking_link"


class ExternalBookingProvider(StrEnum):
    BOOKSY = "booksy"
    OTHER  = "other"


class SubscriptionPlan(StrEnum):
    BOOKSY_LITE       = "booksy_lite"
    BOOKSY_PRO        = "booksy_pro"
    FULL_BOOKING      = "full_booking"
    FULL_BOOKING_PRO  = "full_booking_pro"


class BusinessLanguage(StrEnum):
    """IVR prompt locale for this business (app/core/ivr_prompts.py).
    Plain String column, not a native DB enum -- adding a new locale later
    means adding a _PROMPTS entry plus a new value here, no migration."""
    EN = "en"
    PL = "pl"


class Business(Base):
    __tablename__ = "businesses"
    __table_args__ = (
        Index("ix_businesses_tenant_id", "tenant_id"),
        # Composite FK target for business_memberships (SAC-003): lets a
        # (tenant_id, business_id) foreign key enforce that a membership's
        # business actually belongs to its tenant, at the DB level.
        Index("uix_businesses_tenant_id_id", "tenant_id", "id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(
        String(8), nullable=False, default=BusinessLanguage.EN
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    owner_notification_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    transfer_phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    transfer_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transfer_destination_policy: Mapped[str] = mapped_column(
        String(32), nullable=False, default=TransferDestinationPolicy.BUSINESS_PHONE
    )
    # Dimension 1 — operational: controls who owns the booking flow
    booking_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default=BookingMode.INTERNAL_BOOKING
    )
    external_booking_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_booking_label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_booking_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Dimension 2 — commercial: controls what features the plan includes
    subscription_plan: Mapped[str] = mapped_column(
        String(32), nullable=False, default=SubscriptionPlan.FULL_BOOKING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
