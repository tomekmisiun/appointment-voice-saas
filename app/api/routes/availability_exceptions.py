from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
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
)


@router.post(
    "", response_model=AvailabilityExceptionRead, status_code=status.HTTP_201_CREATED
)
def create_exception_endpoint(
    business_id: int,
    body: AvailabilityExceptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
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


@router.delete("/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exception_endpoint(
    business_id: int,
    exception_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    delete_availability_exception(
        db, exception_id, current_user.tenant_id, business_id=business_id
    )
