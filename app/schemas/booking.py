from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.booking import BookingSource, BookingStatus


class BookingCreate(BaseModel):
    customer_id: int
    service_id: int
    staff_id: int | None = None
    starts_at: datetime
    source: BookingSource = BookingSource.API

    @model_validator(mode="after")
    def starts_at_must_be_aware(self) -> "BookingCreate":
        if self.starts_at.tzinfo is None:
            raise ValueError("starts_at must be timezone-aware")
        return self


class BookingRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    customer_id: int
    service_id: int
    staff_id: int | None
    starts_at: datetime
    ends_at: datetime
    status: str
    source: str
    cancel_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BookingCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


__all__ = [
    "BookingCancelRequest",
    "BookingCreate",
    "BookingRead",
    "BookingSource",
    "BookingStatus",
]
