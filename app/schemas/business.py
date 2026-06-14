from datetime import datetime

from pydantic import BaseModel, Field


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    timezone: str = Field(min_length=1, max_length=64, examples=["Europe/Warsaw"])
    phone: str | None = Field(default=None, max_length=32)


class BusinessRead(BaseModel):
    id: int
    tenant_id: int
    name: str
    timezone: str
    phone: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BusinessUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    phone: str | None = Field(default=None, max_length=32)
    is_active: bool | None = None
