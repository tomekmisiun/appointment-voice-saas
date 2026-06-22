from datetime import date, time

from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.availability_exception import AvailabilityException
from app.services.business_service import require_business
from app.services.staff_service import require_staff_in_business


def _ensure_no_conflicting_exception(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    staff_id: int | None,
    exception_date: date,
    is_closed: bool,
    start_time: time | None,
    end_time: time | None,
) -> None:
    """One-off staff/business block hardening (P3-004): reject a new
    exception that conflicts with an existing one for the exact same
    (business_id, staff_id, date) scope.

    A full-day closure (is_closed=True) can't coexist with any other row
    for that scope/date -- there'd be nothing left for a second row to mean.
    Two "special hours" rows (is_closed=False) for that scope/date are
    allowed (that's the existing, intentional pattern for carving a lunch
    block out of the day -- e.g. 9-12 and 13-17 instead of 9-17), but their
    time windows must not overlap each other.

    Deliberately scoped to an *exact* staff_id match (including NULL for a
    business-wide row) -- this does not cross-check a staff-specific row
    against a business-wide row for the same date, since resolving that
    precedence is P3-002/003's job (salon-vs-staff hours intersection), not
    this one-off-block hardening task.
    """
    staff_filter = (
        AvailabilityException.staff_id.is_(None)
        if staff_id is None
        else AvailabilityException.staff_id == staff_id
    )
    existing = (
        db.query(AvailabilityException)
        .filter(
            AvailabilityException.business_id == business_id,
            AvailabilityException.tenant_id == tenant_id,
            staff_filter,
            AvailabilityException.date == exception_date,
        )
        .all()
    )
    if not existing:
        return
    if is_closed or any(e.is_closed for e in existing):
        raise ConflictError(
            "A full-day closure cannot be combined with another availability "
            "exception for the same business/staff/date"
        )
    for e in existing:
        if e.start_time < end_time and e.end_time > start_time:
            raise ConflictError(
                "This availability exception's time window overlaps with an "
                "existing one for the same business/staff/date"
            )


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
    if staff_id is not None:
        require_staff_in_business(db, staff_id, business_id, tenant_id)
    _ensure_no_conflicting_exception(
        db,
        business_id=business_id,
        tenant_id=tenant_id,
        staff_id=staff_id,
        exception_date=exception_date,
        is_closed=is_closed,
        start_time=start_time,
        end_time=end_time,
    )
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


def require_availability_exception_in_business(
    db: Session, exception_id: int, business_id: int, tenant_id: int
) -> AvailabilityException:
    """Like require_availability_exception(), but also rejects an exception
    that belongs to a different business within the same tenant."""
    exc = require_availability_exception(db, exception_id, tenant_id)
    if exc.business_id != business_id:
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
    db: Session, exception_id: int, tenant_id: int, *, business_id: int
) -> None:
    exc = require_availability_exception_in_business(db, exception_id, business_id, tenant_id)
    db.delete(exc)
    db.commit()
