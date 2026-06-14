from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        Index("ix_services_tenant_id", "tenant_id"),
        Index("ix_services_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    price_minor_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
