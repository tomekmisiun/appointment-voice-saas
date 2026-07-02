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


class BookingPublicRead(BaseModel):
    """Minimal read-only view for unauthenticated public manage-booking pages."""

    id: int
    status: str
    starts_at: datetime
    ends_at: datetime

    model_config = {"from_attributes": True}


class BookingCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class BookingOverrideCreateRequest(BaseModel):
    customer_id: int
    service_id: int
    staff_id: int | None = None
    starts_at: datetime
    source: BookingSource = BookingSource.API
    reason: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def starts_at_must_be_aware(self) -> "BookingOverrideCreateRequest":
        if self.starts_at.tzinfo is None:
            raise ValueError("starts_at must be timezone-aware")
        return self

    @model_validator(mode="after")
    def reason_must_not_be_blank(self) -> "BookingOverrideCreateRequest":
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        return self


class BookingOverrideCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def reason_must_not_be_blank(self) -> "BookingOverrideCancelRequest":
        if not self.reason.strip():
            raise ValueError("reason must not be blank")
        return self


class BookingRescheduleRequest(BaseModel):
    new_starts_at: datetime
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def new_starts_at_must_be_aware(self) -> "BookingRescheduleRequest":
        if self.new_starts_at.tzinfo is None:
            raise ValueError("new_starts_at must be timezone-aware")
        return self


__all__ = [
    "BookingCancelRequest",
    "BookingCreate",
    "BookingOverrideCancelRequest",
    "BookingOverrideCreateRequest",
    "BookingPublicRead",
    "BookingRead",
    "BookingRescheduleRequest",
    "BookingSource",
    "BookingStatus",
]
