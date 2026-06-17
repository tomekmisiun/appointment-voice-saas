from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class LeadBookingModeInterest(StrEnum):
    EXTERNAL_BOOKING_LINK = "external_booking_link"
    STANDALONE_BOOKING    = "standalone_booking"
    UNSURE                = "unsure"


class LeadStatus(StrEnum):
    NEW       = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    ONBOARDED = "onboarded"
    REJECTED  = "rejected"


class OwnerLead(Base):
    """Pre-signup pilot lead submitted via the public intake form.

    Not tenant-scoped — leads represent potential new tenants, so they
    exist outside any existing tenant boundary.  The platform operator
    (default-tenant admin) reads and updates them manually during onboarding.
    """
    __tablename__ = "owner_leads"
    __table_args__ = (
        Index("ix_owner_leads_status", "status"),
        Index("ix_owner_leads_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    booking_mode_interest: Mapped[str] = mapped_column(String(32), nullable=False)
    external_booking_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=LeadStatus.NEW
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
