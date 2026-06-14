from datetime import date, time

from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.availability_exception import AvailabilityException
from app.services.business_service import require_business


def create_availability_exception(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    staff_id: int | None,
    exception_date: date,
    is_closed: bool,
    start_time: time | None,
    end_time: time | None,
    reason: str | None,
) -> AvailabilityException:
    require_business(db, business_id, tenant_id)
    exc = AvailabilityException(
        tenant_id=tenant_id,
        business_id=business_id,
        staff_id=staff_id,
        date=exception_date,
        is_closed=is_closed,
        start_time=start_time,
        end_time=end_time,
        reason=reason,
    )
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


def get_availability_exception(
    db: Session, exception_id: int, tenant_id: int
) -> AvailabilityException | None:
    return (
        db.query(AvailabilityException)
        .filter(
            AvailabilityException.id == exception_id,
            AvailabilityException.tenant_id == tenant_id,
        )
        .first()
    )


def require_availability_exception(
    db: Session, exception_id: int, tenant_id: int
) -> AvailabilityException:
    exc = get_availability_exception(db, exception_id, tenant_id)
    if exc is None:
        raise NotFoundError("Availability exception not found")
    return exc


def list_availability_exceptions(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    staff_id: int | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[AvailabilityException]:
    query = db.query(AvailabilityException).filter(
        AvailabilityException.business_id == business_id,
        AvailabilityException.tenant_id == tenant_id,
    )
    if staff_id is not None:
        query = query.filter(AvailabilityException.staff_id == staff_id)
    if from_date is not None:
        query = query.filter(AvailabilityException.date >= from_date)
    if to_date is not None:
        query = query.filter(AvailabilityException.date <= to_date)
    return query.order_by(AvailabilityException.date.asc()).all()


def delete_availability_exception(
    db: Session, exception_id: int, tenant_id: int
) -> None:
    exc = require_availability_exception(db, exception_id, tenant_id)
    db.delete(exc)
    db.commit()
