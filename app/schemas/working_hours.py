from datetime import time

from pydantic import BaseModel, Field, model_validator


class WorkingHoursCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def end_after_start(self) -> "WorkingHoursCreate":
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class WorkingHoursRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    staff_id: int | None
    day_of_week: int
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}
