import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_log import AuditAction, AuditLog

logger = logging.getLogger("app.audit_logs")


def create_audit_log(
    db: Session,
    tenant_id: int,
    admin_id: int | None,
    action: AuditAction,
    target_user_id: int | None = None,
    target_booking_id: int | None = None,
    target_staff_id: int | None = None,
    source: str | None = None,
    *,
    commit: bool = True,
) -> AuditLog:
    audit_log = AuditLog(
        tenant_id=tenant_id,
        admin_id=admin_id,
        action=action.value,
        target_user_id=target_user_id,
        target_booking_id=target_booking_id,
        target_staff_id=target_staff_id,
        source=source,
    )

    db.add(audit_log)

    if commit:
        db.commit()
        db.refresh(audit_log)
    else:
        db.flush()

    return audit_log


def get_audit_logs(
    db: Session,
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
    action: AuditAction | None = None,
    admin_id: int | None = None,
    target_user_id: int | None = None,
) -> list[AuditLog]:
    query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)

    if action is not None:
        query = query.filter(AuditLog.action == action.value)

    if admin_id is not None:
        query = query.filter(AuditLog.admin_id == admin_id)

    if target_user_id is not None:
        query = query.filter(AuditLog.target_user_id == target_user_id)

    return (
        query
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def cleanup_old_audit_logs(db: Session) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.audit_log_retention_days,
    )
    deleted_count = (
        db.query(AuditLog)
        .filter(AuditLog.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()

    logger.info(
        "audit_logs_cleaned count=%s cutoff=%s",
        deleted_count,
        cutoff.isoformat(),
    )

    return deleted_count
