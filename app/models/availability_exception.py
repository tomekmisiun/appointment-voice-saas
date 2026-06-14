from datetime import date, time

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AvailabilityException(Base):
    __tablename__ = "availability_exceptions"
    __table_args__ = (
        Index("ix_availability_exceptions_tenant_id", "tenant_id"),
        Index("ix_availability_exceptions_business_id", "business_id"),
        Index("ix_availability_exceptions_staff_id", "staff_id"),
        Index("ix_availability_exceptions_date", "date"),
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
    date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    start_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    end_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
