from datetime import time

from pydantic import BaseModel, Field, model_validator


class RecurringStaffBlockCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=255)
    staff_id: int | None = Field(
        default=None,
        description="Omit or null for a business-wide block; set to scope it to one staff member.",
    )

    @model_validator(mode="after")
    def end_after_start(self) -> "RecurringStaffBlockCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class RecurringStaffBlockRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    staff_id: int | None
    day_of_week: int
    start_time: time
    end_time: time
    reason: str | None

    model_config = {"from_attributes": True}
