from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    duration_minutes: int = Field(ge=1, le=480)
    price_minor_units: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    deposit_required: bool = False
    deposit_minor_units: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def deposit_fields_required_when_deposit_required(self) -> "ServiceCreate":
        if self.deposit_required and (self.deposit_minor_units is None or self.currency is None):
            raise ValueError(
                "deposit_minor_units and currency are required when deposit_required is true"
            )
        return self


class ServiceRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    name: str
    duration_minutes: int
    is_active: bool
    price_minor_units: int | None
    currency: str | None
    deposit_required: bool
    deposit_minor_units: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    duration_minutes: int | None = Field(default=None, ge=1, le=480)
    price_minor_units: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    is_active: bool | None = None
    deposit_required: bool | None = None
    deposit_minor_units: int | None = Field(default=None, ge=0)
