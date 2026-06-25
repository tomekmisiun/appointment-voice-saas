from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StaffCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    contact_email: EmailStr | None = None
    position: str | None = Field(default=None, max_length=128)
    accepts_bookings: bool = True
    is_customer_visible: bool = True


class StaffRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    name: str
    phone: str | None
    contact_email: str | None
    position: str | None
    accepts_bookings: bool
    is_customer_visible: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    contact_email: EmailStr | None = None
    position: str | None = Field(default=None, max_length=128)
    accepts_bookings: bool | None = None
    is_customer_visible: bool | None = None
    # Lifecycle: prefer POST /{id}/deactivate and /{id}/reactivate which emit
    # audit logs. This field is kept for backward compatibility with existing
    # PATCH clients; it is routed through the same audit-emitting functions.
    is_active: bool | None = None
