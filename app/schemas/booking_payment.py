from datetime import datetime

from pydantic import BaseModel, Field

from app.models.booking_payment import BookingPaymentStatus


class BookingPaymentRead(BaseModel):
    id: int
    booking_id: int
    provider: str
    provider_session_id: str | None
    provider_payment_id: str | None
    amount_minor_units: int
    currency: str
    status: BookingPaymentStatus
    failure_reason: str | None
    created_at: datetime
    paid_at: datetime | None
    refunded_at: datetime | None

    model_config = {"from_attributes": True}


class BookingPaymentRefundRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


__all__ = ["BookingPaymentRead", "BookingPaymentRefundRequest"]
