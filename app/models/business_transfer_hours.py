from datetime import time

from sqlalchemy import ForeignKey, Index, Integer, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BusinessTransferHours(Base):
    __tablename__ = "business_transfer_hours"
    __table_args__ = (
        UniqueConstraint("business_id", "day_of_week", "start_time", name="uq_bth_business_day_start"),
        Index("ix_business_transfer_hours_tenant_id", "tenant_id"),
        Index("ix_business_transfer_hours_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
