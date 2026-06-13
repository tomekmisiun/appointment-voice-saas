from datetime import datetime

from pydantic import BaseModel

from app.models.audit_log import AuditAction


class AuditLogRead(BaseModel):
    id: int
    admin_id: int | None
    action: AuditAction
    target_user_id: int | None
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }
