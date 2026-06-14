from datetime import datetime

from pydantic import BaseModel, Field


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)


class StaffRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    name: str
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
