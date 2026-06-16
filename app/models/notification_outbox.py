from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class NotificationChannel(StrEnum):
    SMS = "sms"


class NotificationPurpose(StrEnum):
    BOOKING_CONFIRMATION  = "booking_confirmation"
    BOOKING_CANCELLATION  = "booking_cancellation"
    EXTERNAL_BOOKING_LINK = "external_booking_link"   # link SMS — no booking_id


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index("ix_notification_outbox_tenant_id", "tenant_id"),
        Index("ix_notification_outbox_business_id", "business_id"),
        Index("ix_notification_outbox_booking_id", "booking_id"),
        Index("ix_notification_outbox_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    booking_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bookings.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NotificationChannel.SMS
    )
    purpose: Mapped[str] = mapped_column(String(64), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=NotificationStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
