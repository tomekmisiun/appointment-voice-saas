from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.business_transfer_hours import BusinessTransferHoursCreate, BusinessTransferHoursRead
from app.services.business_transfer_hours_service import (
    create_transfer_hours,
    delete_transfer_hours,
    list_transfer_hours,
    require_transfer_hours,
)

router = APIRouter(
    prefix="/businesses/{business_id}/transfer-hours", tags=["transfer-hours"]
)


@router.post("", response_model=BusinessTransferHoursRead, status_code=status.HTTP_201_CREATED)
def create_transfer_hours_endpoint(
    business_id: int,
    body: BusinessTransferHoursCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return create_transfer_hours(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        day_of_week=body.day_of_week,
        start_time=body.start_time,
        end_time=body.end_time,
    )


@router.get("", response_model=list[BusinessTransferHoursRead])
def list_transfer_hours_endpoint(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_transfer_hours(db, business_id, current_user.tenant_id)


@router.get("/{entry_id}", response_model=BusinessTransferHoursRead)
def get_transfer_hours_endpoint(
    business_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_transfer_hours(db, entry_id, business_id, current_user.tenant_id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer_hours_endpoint(
    business_id: int,
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    delete_transfer_hours(db, entry_id, business_id, current_user.tenant_id)
