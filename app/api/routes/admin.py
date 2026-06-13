from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_permission
from app.core.permissions import Permission
from app.api.openapi import ADMIN_ERROR_RESPONSES
from app.db.session import get_db
from app.models.audit_log import AuditAction
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.audit_log_service import get_audit_logs

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get(
    "",
    summary="Admin panel welcome payload",
    responses=ADMIN_ERROR_RESPONSES,
)
def admin_panel(
    current_user: User = Depends(require_permission(Permission.ADMIN_ACCESS)),
):
    return {
        "message": "Welcome admin",
        "email": current_user.email,
    }


@router.get(
    "/audit-logs",
    response_model=list[AuditLogRead],
    summary="List audit logs",
    description="Admin-only paginated audit log listing with action and actor filters.",
    responses=ADMIN_ERROR_RESPONSES,
)
def list_audit_logs(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    action: AuditAction | None = None,
    admin_id: int | None = Query(None, ge=1),
    target_user_id: int | None = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AUDIT_LOGS_LIST)),
):
    skip = (page - 1) * size

    return get_audit_logs(
        db,
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=size,
        action=action,
        admin_id=admin_id,
        target_user_id=target_user_id,
    )
