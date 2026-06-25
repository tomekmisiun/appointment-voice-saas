from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.membership import require_business_member
from app.models.business_membership import MembershipRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate
from app.services.staff_service import (
    create_staff,
    list_staff,
    require_staff_in_business,
    update_staff,
)

router = APIRouter(prefix="/businesses/{business_id}/staff", tags=["staff"])


@router.post("", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
def create_staff_endpoint(
    business_id: int,
    body: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return create_staff(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        name=body.name,
        phone=body.phone,
    )


@router.get("", response_model=list[StaffRead])
def list_staff_endpoint(
    business_id: int,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return list_staff(
        db,
        business_id,
        current_user.tenant_id,
        include_inactive=include_inactive,
        skip=skip,
        limit=size,
    )


@router.get("/{staff_id}", response_model=StaffRead)
def get_staff_endpoint(
    business_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_staff_in_business(db, staff_id, business_id, current_user.tenant_id)


@router.patch("/{staff_id}", response_model=StaffRead)
def update_staff_endpoint(
    business_id: int,
    staff_id: int,
    body: StaffUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return update_staff(
        db,
        staff_id,
        business_id,
        current_user.tenant_id,
        name=body.name,
        phone=body.phone,
        is_active=body.is_active,
    )
