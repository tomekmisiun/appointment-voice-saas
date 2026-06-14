from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    phone: str = Field(min_length=1, max_length=32)
    name: str | None = Field(default=None, max_length=255)


class CustomerRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    phone: str
    phone_normalized: str
    name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
