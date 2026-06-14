from datetime import datetime

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    duration_minutes: int = Field(ge=1, le=480)
    price_minor_units: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ServiceRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    name: str
    duration_minutes: int
    is_active: bool
    price_minor_units: int | None
    currency: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    price_minor_units: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
