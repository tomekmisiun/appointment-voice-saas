from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.owner_lead import LeadBookingModeInterest, LeadStatus

_ALLOWED_URL_SCHEMES = ("http://", "https://")


def _validate_booking_url(url: str | None) -> str | None:
    if url is None:
        return url
    url = url.strip()
    if "\n" in url or "\r" in url:
        raise ValueError("external_booking_url must not contain newlines")
    if not any(url.lower().startswith(s) for s in _ALLOWED_URL_SCHEMES):
        raise ValueError("external_booking_url must start with http:// or https://")
    return url


class OwnerLeadCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=255)
    owner_name: str | None = Field(default=None, max_length=255)
    email: EmailStr
    phone_number: str = Field(min_length=1, max_length=32)
    city: str | None = Field(default=None, max_length=128)
    booking_mode_interest: LeadBookingModeInterest
    external_booking_url: str | None = Field(default=None, max_length=512)
    message: str | None = Field(default=None, max_length=1000)

    @field_validator("external_booking_url", mode="after")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        return _validate_booking_url(v)

    @model_validator(mode="after")
    def url_required_for_external_mode(self) -> "OwnerLeadCreate":
        if (
            self.booking_mode_interest == LeadBookingModeInterest.EXTERNAL_BOOKING_LINK
            and not self.external_booking_url
        ):
            raise ValueError(
                "external_booking_url is required when booking_mode_interest "
                "is external_booking_link"
            )
        return self


class OwnerLeadPublicRead(BaseModel):
    """Response returned to the public submitter — no sensitive internals."""
    id: int
    business_name: str
    booking_mode_interest: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnerLeadAdminRead(BaseModel):
    """Full lead record for platform operators."""
    id: int
    business_name: str
    owner_name: str | None
    email: str
    phone_number: str
    city: str | None
    booking_mode_interest: str
    external_booking_url: str | None
    message: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OwnerLeadStatusUpdate(BaseModel):
    status: LeadStatus
