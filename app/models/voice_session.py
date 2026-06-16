from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class IvrStep(StrEnum):
    INCOMING = "incoming"
    SERVICE_SELECTION = "service_selection"
    SLOT_SELECTION = "slot_selection"
    BOOKING_CONFIRMED = "booking_confirmed"
    NO_SLOTS = "no_slots"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class VoiceSession(Base):
    __tablename__ = "voice_sessions"
    __table_args__ = (
        Index("ix_voice_sessions_tenant_id", "tenant_id"),
        Index("ix_voice_sessions_business_id", "business_id"),
        Index("ix_voice_sessions_step", "step"),
        Index("ix_voice_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False
    )
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id"), nullable=False
    )
    caller_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    step: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IvrStep.INCOMING
    )
    selected_service_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("services.id"), nullable=True
    )
    selected_staff_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=True
    )
    selected_slot_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    selected_slot_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    booking_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("bookings.id"), nullable=True
    )
    slot_candidates: Mapped[str | None] = mapped_column(Text, nullable=True)
    call_sid: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
