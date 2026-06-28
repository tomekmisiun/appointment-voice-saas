from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.business import (
    BookingMode,
    BusinessLanguage,
    ExternalBookingProvider,
    SubscriptionPlan,
    TransferDestinationPolicy,
)

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


def _validate_booking_label(label: str | None) -> str | None:
    if label is None:
        return label
    if "\n" in label or "\r" in label:
        raise ValueError("external_booking_label must not contain newlines")
    return label


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64, examples=["Europe/Warsaw"])
    language: BusinessLanguage = BusinessLanguage.EN
    phone: str | None = Field(default=None, max_length=32)
    owner_notification_phone: str | None = Field(default=None, max_length=32)
    transfer_phone_number: str | None = Field(default=None, max_length=32)
    transfer_enabled: bool = False
    transfer_destination_policy: TransferDestinationPolicy = TransferDestinationPolicy.BUSINESS_PHONE
    booking_mode: BookingMode = BookingMode.INTERNAL_BOOKING
    external_booking_url: str | None = Field(default=None, max_length=512)
    external_booking_label: str | None = Field(default=None, max_length=128)
    external_booking_provider: ExternalBookingProvider | None = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FULL_BOOKING

    @field_validator("external_booking_url", mode="after")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        return _validate_booking_url(v)

    @field_validator("external_booking_label", mode="after")
    @classmethod
    def validate_label(cls, v: str | None) -> str | None:
        return _validate_booking_label(v)

    @model_validator(mode="after")
    def external_url_required_when_external_mode(self) -> "BusinessCreate":
        if (
            self.booking_mode == BookingMode.EXTERNAL_BOOKING_LINK
            and not self.external_booking_url
        ):
            raise ValueError(
                "external_booking_url is required when booking_mode is external_booking_link"
            )
        return self


class BusinessRead(BaseModel):
    id: int
    tenant_id: int
    name: str
    timezone: str
    language: str
    phone: str | None
    owner_notification_phone: str | None
    transfer_phone_number: str | None
    is_active: bool
    transfer_enabled: bool
    transfer_destination_policy: str
    booking_mode: str
    external_booking_url: str | None
    external_booking_label: str | None
    external_booking_provider: str | None
    subscription_plan: str
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    language: BusinessLanguage | None = None
    phone: str | None = Field(default=None, max_length=32)
    owner_notification_phone: str | None = Field(default=None, max_length=32)
    transfer_phone_number: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
    transfer_enabled: bool | None = None
    transfer_destination_policy: TransferDestinationPolicy | None = None
    booking_mode: BookingMode | None = None
    external_booking_url: str | None = Field(default=None, max_length=512)
    external_booking_label: str | None = Field(default=None, max_length=128)
    external_booking_provider: ExternalBookingProvider | None = None
    subscription_plan: SubscriptionPlan | None = None

    @field_validator("external_booking_url", mode="after")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        return _validate_booking_url(v)

    @field_validator("external_booking_label", mode="after")
    @classmethod
    def validate_label(cls, v: str | None) -> str | None:
        return _validate_booking_label(v)

    @model_validator(mode="after")
    def external_url_required_when_external_mode(self) -> "BusinessUpdate":
        if (
            self.booking_mode == BookingMode.EXTERNAL_BOOKING_LINK
            and not self.external_booking_url
        ):
            raise ValueError(
                "external_booking_url is required when booking_mode is external_booking_link"
            )
        return self
