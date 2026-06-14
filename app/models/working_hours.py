from datetime import time

from sqlalchemy import ForeignKey, Index, Integer, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkingHours(Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        Index("ix_working_hours_tenant_id", "tenant_id"),
        Index("ix_working_hours_business_id", "business_id"),
        Index("ix_working_hours_staff_id", "staff_id"),
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
