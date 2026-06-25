from datetime import datetime

from pydantic import BaseModel


class BusinessMembershipRead(BaseModel):
    id: int
    tenant_id: int
    business_id: int
    user_id: int
    staff_id: int | None
    role: str
    status: str
    invited_at: datetime | None
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
