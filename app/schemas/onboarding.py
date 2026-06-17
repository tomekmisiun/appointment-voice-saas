from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.models.business import BookingMode, ExternalBookingProvider, SubscriptionPlan
from app.schemas.business import _validate_booking_url


class OnboardingStaffItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


class OnboardingServiceItem(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    duration_minutes: int = Field(ge=1, le=480)
    price_minor_units: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class OnboardingWorkingHoursItem(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def end_after_start(self) -> "OnboardingWorkingHoursItem":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class OnboardingBusinessSpec(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    booking_mode: BookingMode = BookingMode.INTERNAL_BOOKING
    external_booking_url: str | None = Field(default=None, max_length=512)
    external_booking_label: str | None = Field(default=None, max_length=128)
    external_booking_provider: ExternalBookingProvider | None = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.FULL_BOOKING

    @model_validator(mode="after")
    def external_url_required_when_external_mode(self) -> "OnboardingBusinessSpec":
        url = self.external_booking_url
        if url is not None:
            _validate_booking_url(url)
        if self.booking_mode == BookingMode.EXTERNAL_BOOKING_LINK and not url:
            raise ValueError(
                "external_booking_url is required when booking_mode is external_booking_link"
            )
        return self


class OnboardingSetupRequest(BaseModel):
    business: OnboardingBusinessSpec
    staff: list[OnboardingStaffItem] = Field(default_factory=list)
    services: list[OnboardingServiceItem] = Field(default_factory=list)
    working_hours: list[OnboardingWorkingHoursItem] = Field(default_factory=list)


class OnboardingSetupResponse(BaseModel):
    business_id: int
    business_name: str
    staff_count: int
    service_count: int
    working_hours_count: int
