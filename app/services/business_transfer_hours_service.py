from datetime import time

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.business_transfer_hours import BusinessTransferHours
from app.services.business_service import require_business


def create_transfer_hours(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    day_of_week: int,
    start_time: time,
    end_time: time,
) -> BusinessTransferHours:
    require_business(db, business_id, tenant_id)
    entry = BusinessTransferHours(
        tenant_id=tenant_id,
        business_id=business_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(entry)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("A transfer hours window with this start time already exists for this business and day")
    db.refresh(entry)
    return entry


def get_transfer_hours(
    db: Session, entry_id: int, tenant_id: int, business_id: int
) -> BusinessTransferHours | None:
    return (
        db.query(BusinessTransferHours)
        .filter(
            BusinessTransferHours.id == entry_id,
            BusinessTransferHours.tenant_id == tenant_id,
            BusinessTransferHours.business_id == business_id,
        )
        .first()
    )


def require_transfer_hours(
    db: Session, entry_id: int, business_id: int, tenant_id: int
) -> BusinessTransferHours:
    entry = get_transfer_hours(db, entry_id, tenant_id, business_id)
    if entry is None:
        raise NotFoundError("Transfer hours record not found")
    return entry


def list_transfer_hours(
    db: Session,
    business_id: int,
    tenant_id: int,
) -> list[BusinessTransferHours]:
    return (
        db.query(BusinessTransferHours)
        .filter(
            BusinessTransferHours.business_id == business_id,
            BusinessTransferHours.tenant_id == tenant_id,
        )
        .order_by(BusinessTransferHours.day_of_week.asc(), BusinessTransferHours.start_time.asc())
        .all()
    )


def delete_transfer_hours(db: Session, entry_id: int, business_id: int, tenant_id: int) -> None:
    entry = require_transfer_hours(db, entry_id, business_id, tenant_id)
    db.delete(entry)
    db.commit()
