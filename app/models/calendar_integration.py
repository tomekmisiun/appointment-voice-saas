from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class CalendarIntegration(Base):
    __tablename__ = "calendar_integrations"
    __table_args__ = (
        # One business-level integration per business (staff_id IS NULL)
        Index(
            "uix_calendar_integrations_business_level",
            "business_id",
            unique=True,
            postgresql_where=text("staff_id IS NULL"),
        ),
        # One staff-level integration per staff member per business
        Index(
            "uix_calendar_integrations_staff_level",
            "business_id",
            "staff_id",
            unique=True,
            postgresql_where=text("staff_id IS NOT NULL"),
        ),
        Index("ix_calendar_integrations_tenant_id", "tenant_id"),
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
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
