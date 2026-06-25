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
    deactivate_staff,
    list_staff,
    reactivate_staff,
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
        contact_email=body.contact_email,
        position=body.position,
        accepts_bookings=body.accepts_bookings,
        is_customer_visible=body.is_customer_visible,
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
    # Use model_fields_set so explicit null values clear the DB field while
    # omitted fields are left untouched.
    update_data = body.model_dump(include=body.model_fields_set)
    is_active = update_data.pop("is_active", None)

    if update_data:
        update_staff(
            db,
            staff_id,
            business_id,
            current_user.tenant_id,
            _always_set=update_data,
        )

    # Route activation changes through the audit-emitting service functions.
    if is_active is False:
        return deactivate_staff(
            db, staff_id, business_id, current_user.tenant_id,
            actor_id=current_user.id,
        )
    if is_active is True:
        return reactivate_staff(
            db, staff_id, business_id, current_user.tenant_id,
            actor_id=current_user.id,
        )

    return require_staff_in_business(db, staff_id, business_id, current_user.tenant_id)


@router.post("/{staff_id}/deactivate", response_model=StaffRead)
def deactivate_staff_endpoint(
    business_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return deactivate_staff(
        db,
        staff_id,
        business_id,
        current_user.tenant_id,
        actor_id=current_user.id,
    )


@router.post("/{staff_id}/reactivate", response_model=StaffRead)
def reactivate_staff_endpoint(
    business_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return reactivate_staff(
        db,
        staff_id,
        business_id,
        current_user.tenant_id,
        actor_id=current_user.id,
    )
