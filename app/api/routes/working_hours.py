from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.working_hours import WorkingHoursCreate, WorkingHoursRead, WorkingHoursUpdate
from app.services.working_hours_service import (
    create_working_hours,
    delete_working_hours,
    list_working_hours,
    require_working_hours_in_business,
    update_working_hours,
)

router = APIRouter(
    prefix="/businesses/{business_id}/working-hours", tags=["working-hours"]
)


@router.post("", response_model=WorkingHoursRead, status_code=status.HTTP_201_CREATED)
def create_working_hours_endpoint(
    business_id: int,
    body: WorkingHoursCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Create a recurring weekly working-hours window (P3-001).

    Omit `staff_id` (or send it as null) for a business-wide "salon hours"
    window -- used when availability is searched without a specific staff
    member (e.g. "any available staff"). Set `staff_id` to scope the window
    to one staff member instead -- required before that staff member can be
    offered in the IVR staff-selection menu (P2-006) or have their own
    availability searched, since `get_available_slots()` only consults a
    given staff_id's own rows, never falling back to the business-wide ones,
    for a staff-specific search. Combining both kinds of hours for a single
    search (salon-wide intersected with staff-specific) is P3-002, not this
    endpoint."""
    return create_working_hours(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        staff_id=body.staff_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
    )


@router.get("", response_model=list[WorkingHoursRead])
def list_working_hours_endpoint(
    business_id: int,
    staff_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_working_hours(
        db,
        business_id,
        current_user.tenant_id,
        staff_id=staff_id,
    )


@router.get("/{wh_id}", response_model=WorkingHoursRead)
def get_working_hours_endpoint(
    business_id: int,
    wh_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_working_hours_in_business(db, wh_id, business_id, current_user.tenant_id)


@router.patch("/{wh_id}", response_model=WorkingHoursRead)
def update_working_hours_endpoint(
    business_id: int,
    wh_id: int,
    body: WorkingHoursUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return update_working_hours(
        db, wh_id, current_user.tenant_id,
        business_id=business_id,
        start_time=body.start_time,
        end_time=body.end_time,
    )


@router.delete("/{wh_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_working_hours_endpoint(
    business_id: int,
    wh_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    delete_working_hours(db, wh_id, current_user.tenant_id, business_id=business_id)
