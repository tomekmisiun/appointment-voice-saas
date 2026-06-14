from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "phone_normalized",
            name="uq_customers_business_phone",
        ),
        Index("ix_customers_tenant_id", "tenant_id"),
        Index("ix_customers_business_id", "business_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
