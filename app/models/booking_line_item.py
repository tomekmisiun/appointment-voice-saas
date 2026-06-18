from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class BookingLineItem(Base):
    """One ordered service within a multi-service booking (P2-008).

    Additive alongside Booking.service_id, which remains the booking's
    primary/first service for all existing single-service code paths
    (IVR, availability search, calendar sync). duration_minutes is a
    snapshot taken when the line item is added, so a later change to
    Service.duration_minutes doesn't retroactively alter what was booked.
    """

    __tablename__ = "booking_line_items"
    __table_args__ = (
        UniqueConstraint("booking_id", "position", name="uq_booking_line_items_booking_position"),
        Index("ix_booking_line_items_tenant_id", "tenant_id"),
        Index("ix_booking_line_items_business_id", "business_id"),
        Index("ix_booking_line_items_booking_id", "booking_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    booking_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bookings.id"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
