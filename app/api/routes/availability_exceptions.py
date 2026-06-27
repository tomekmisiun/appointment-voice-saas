from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_demo_business_access, require_non_demo_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.availability_exception import (
    AvailabilityExceptionCreate,
    AvailabilityExceptionRead,
)
from app.services.availability_exception_service import (
    create_availability_exception,
    delete_availability_exception,
    list_availability_exceptions,
    require_availability_exception_in_business,
)

router = APIRouter(
    prefix="/businesses/{business_id}/availability-exceptions",
    tags=["availability-exceptions"],
    dependencies=[Depends(require_demo_business_access)],
)


@router.post(
    "",
    response_model=AvailabilityExceptionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_non_demo_user)],
)
def create_exception_endpoint(
    business_id: int,
    body: AvailabilityExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a one-off date override -- a full closure or special hours
    for a single date (P3-003/P3-004).

    Omit `staff_id` (or send it as null) for a business-wide closure or
    holiday: it removes every slot for every staff member that date,
    regardless of their own hours or any staff-specific exception for the
    same date -- a business-wide `is_closed=True` row always wins
    (`get_available_slots()` closes the day the moment *any* matching
    exception is closed, business-wide or staff-specific). Set `staff_id`
    to scope the override to one staff member instead -- it has no effect
    on other staff members' availability or on a search with no staff_id
    ("any available staff").

    For recurring closures (e.g. every Sunday) use `WorkingHours` (simply
    don't create a row for that weekday) rather than one exception per
    date. For a recurring partial block (e.g. a daily lunch break), use
    `POST /businesses/{business_id}/recurring-staff-blocks` instead (P3-005,
    see `docs/adr/0003-recurring-staff-blocks.md`)."""
    return create_availability_exception(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        staff_id=body.staff_id,
        exception_date=body.date,
        is_closed=body.is_closed,
        start_time=body.start_time,
        end_time=body.end_time,
        reason=body.reason,
    )


@router.get("", response_model=list[AvailabilityExceptionRead])
def list_exceptions_endpoint(
    business_id: int,
    staff_id: int | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_availability_exceptions(
        db,
        business_id,
        current_user.tenant_id,
        staff_id=staff_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/{exception_id}", response_model=AvailabilityExceptionRead)
def get_exception_endpoint(
    business_id: int,
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_availability_exception_in_business(
        db, exception_id, business_id, current_user.tenant_id
    )


@router.delete(
    "/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_non_demo_user)],
)
def delete_exception_endpoint(
    business_id: int,
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    delete_availability_exception(
        db, exception_id, current_user.tenant_id, business_id=business_id
    )
