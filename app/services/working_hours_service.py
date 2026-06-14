from datetime import time

from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.working_hours import WorkingHours
from app.services.business_service import require_business


def create_working_hours(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    staff_id: int | None,
    day_of_week: int,
    start_time: time,
    end_time: time,
) -> WorkingHours:
    require_business(db, business_id, tenant_id)
    wh = WorkingHours(
        tenant_id=tenant_id,
        business_id=business_id,
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


def get_working_hours(db: Session, wh_id: int, tenant_id: int) -> WorkingHours | None:
    return (
        db.query(WorkingHours)
        .filter(WorkingHours.id == wh_id, WorkingHours.tenant_id == tenant_id)
        .first()
    )


def require_working_hours(db: Session, wh_id: int, tenant_id: int) -> WorkingHours:
    wh = get_working_hours(db, wh_id, tenant_id)
    if wh is None:
        raise NotFoundError("Working hours record not found")
    return wh


def list_working_hours(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    staff_id: int | None = None,
) -> list[WorkingHours]:
    query = db.query(WorkingHours).filter(
        WorkingHours.business_id == business_id,
        WorkingHours.tenant_id == tenant_id,
    )
    if staff_id is not None:
        query = query.filter(WorkingHours.staff_id == staff_id)
    return query.order_by(WorkingHours.day_of_week.asc(), WorkingHours.start_time.asc()).all()


def delete_working_hours(db: Session, wh_id: int, tenant_id: int) -> None:
    wh = require_working_hours(db, wh_id, tenant_id)
    db.delete(wh)
    db.commit()
