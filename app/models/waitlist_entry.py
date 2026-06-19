from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class WaitlistEntryStatus(StrEnum):
    WAITING = "waiting"
    OFFERED = "offered"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WaitlistEntry(Base):
    """A customer's desire for a service (and optionally a specific staff
    member) on a given date, recorded when no slot was available (P2-010).
    Purely a data model: nothing creates these from the cancellation flow
    or offers them automatically yet (P2-011), and nothing expires/escalates
    them yet (P2-012)."""

    __tablename__ = "waitlist_entries"
    __table_args__ = (
        Index("ix_waitlist_entries_tenant_id", "tenant_id"),
        Index("ix_waitlist_entries_business_id", "business_id"),
        Index("ix_waitlist_entries_status", "status"),
        Index(
            "ix_waitlist_entries_business_service_date",
            "business_id",
            "service_id",
            "desired_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False
    )
    service_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=False
    )
    staff_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=True
    )
    # The staff member of the actual freed-up slot this entry was last
    # offered for (P2-012) -- distinct from staff_id, the customer's own
    # preference, which may be NULL ("any staff") even when the slot they
    # were offered belonged to a specific staff member.
    offered_for_staff_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=True
    )
    desired_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=WaitlistEntryStatus.WAITING
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
