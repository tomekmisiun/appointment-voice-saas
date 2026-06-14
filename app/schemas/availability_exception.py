from datetime import date, time

from pydantic import BaseModel, Field, model_validator


class AvailabilityExceptionCreate(BaseModel):
    date: date
    is_closed: bool = True
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=255)
    staff_id: int | None = None

    @model_validator(mode="after")
    def validate_special_hours(self) -> "AvailabilityExceptionCreate":
        if not self.is_closed:
            if self.start_time is None or self.end_time is None:
                raise ValueError(
                    "start_time and end_time are required when is_closed is False"
                )
            if self.end_time <= self.start_time:
                raise ValueError("end_time must be after start_time")
        return self


class AvailabilityExceptionRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    staff_id: int | None
    date: date
    is_closed: bool
    start_time: time | None
    end_time: time | None
    reason: str | None

    model_config = {"from_attributes": True}
