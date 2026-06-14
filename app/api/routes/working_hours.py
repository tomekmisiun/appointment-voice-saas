from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.working_hours import WorkingHoursCreate, WorkingHoursRead
from app.services.working_hours_service import (
    create_working_hours,
    delete_working_hours,
    list_working_hours,
    require_working_hours,
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
    return create_working_hours(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        staff_id=None,
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
    return require_working_hours(db, wh_id, current_user.tenant_id)


@router.delete("/{wh_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_working_hours_endpoint(
    business_id: int,
    wh_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    delete_working_hours(db, wh_id, current_user.tenant_id)
