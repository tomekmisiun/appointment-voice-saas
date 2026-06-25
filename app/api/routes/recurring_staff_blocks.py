from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.membership import require_business_member
from app.models.business_membership import MembershipRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.recurring_staff_block import (
    RecurringStaffBlockCreate,
    RecurringStaffBlockRead,
)
from app.services.recurring_staff_block_service import (
    create_recurring_staff_block,
    delete_recurring_staff_block,
    list_recurring_staff_blocks,
    require_recurring_staff_block_in_business,
)

router = APIRouter(
    prefix="/businesses/{business_id}/recurring-staff-blocks",
    tags=["recurring-staff-blocks"],
)


@router.post(
    "", response_model=RecurringStaffBlockRead, status_code=status.HTTP_201_CREATED
)
def create_recurring_staff_block_endpoint(
    business_id: int,
    body: RecurringStaffBlockCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    """Create a recurring weekly unavailable window (P3-005), e.g. a daily
    lunch break. Unlike a one-off `AvailabilityException`, this is
    subtracted from generated slots every matching weekday and stays
    correct if working hours change later -- see
    `docs/adr/0003-recurring-staff-blocks.md`.

    Omit `staff_id` (or send it as null) for a business-wide block (applies
    to every staff member's search and an "any available staff" search).
    Set `staff_id` to scope it to one staff member -- it has no effect on
    other staff members or a search with no staff_id."""
    return create_recurring_staff_block(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        staff_id=body.staff_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
        reason=body.reason,
    )


@router.get("", response_model=list[RecurringStaffBlockRead])
def list_recurring_staff_blocks_endpoint(
    business_id: int,
    staff_id: int | None = Query(default=None),
    day_of_week: int | None = Query(default=None, ge=0, le=6),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_recurring_staff_blocks(
        db,
        business_id,
        current_user.tenant_id,
        staff_id=staff_id,
        day_of_week=day_of_week,
    )


@router.get("/{block_id}", response_model=RecurringStaffBlockRead)
def get_recurring_staff_block_endpoint(
    business_id: int,
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_recurring_staff_block_in_business(
        db, block_id, business_id, current_user.tenant_id
    )


@router.delete("/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_staff_block_endpoint(
    business_id: int,
    block_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    delete_recurring_staff_block(
        db, block_id, current_user.tenant_id, business_id=business_id
    )
