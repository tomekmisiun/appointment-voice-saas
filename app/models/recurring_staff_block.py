from datetime import time

from sqlalchemy import ForeignKey, Index, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecurringStaffBlock(Base):
    """Recurring weekly unavailable window (P3-005, ADR 0003). Subtracted
    from generated availability slots rather than replacing a window like
    `AvailabilityException` does -- see `app/services/availability_service.py`
    and `docs/adr/0003-recurring-staff-blocks.md` for why."""

    __tablename__ = "recurring_staff_blocks"
    __table_args__ = (
        Index("ix_recurring_staff_blocks_tenant_id", "tenant_id"),
        Index("ix_recurring_staff_blocks_business_id", "business_id"),
        Index("ix_recurring_staff_blocks_staff_id", "staff_id"),
        Index("ix_recurring_staff_blocks_day_of_week", "day_of_week"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    staff_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
