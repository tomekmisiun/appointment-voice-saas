from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.membership import require_business_member
from app.models.business_membership import MembershipRole
from app.db.session import get_db
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate
from app.services.service_service import (
    create_service,
    delete_service,
    list_services,
    require_service_in_business,
    update_service,
)

router = APIRouter(prefix="/businesses/{business_id}/services", tags=["services"])


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service_endpoint(
    business_id: int,
    body: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return create_service(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        name=body.name,
        duration_minutes=body.duration_minutes,
        price_minor_units=body.price_minor_units,
        currency=body.currency,
        deposit_required=body.deposit_required,
        deposit_minor_units=body.deposit_minor_units,
    )


@router.get("", response_model=list[ServiceRead])
def list_services_endpoint(
    business_id: int,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return list_services(
        db,
        business_id,
        current_user.tenant_id,
        include_inactive=include_inactive,
        skip=skip,
        limit=size,
    )


@router.get("/{service_id}", response_model=ServiceRead)
def get_service_endpoint(
    business_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_service_in_business(db, service_id, business_id, current_user.tenant_id)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service_endpoint(
    business_id: int,
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    delete_service(db, service_id, current_user.tenant_id, business_id=business_id)


@router.patch("/{service_id}", response_model=ServiceRead)
def update_service_endpoint(
    business_id: int,
    service_id: int,
    body: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business_member(MembershipRole.OWNER, MembershipRole.ADMIN)),
):
    return update_service(
        db,
        service_id,
        business_id,
        current_user.tenant_id,
        name=body.name,
        duration_minutes=body.duration_minutes,
        price_minor_units=body.price_minor_units,
        currency=body.currency,
        is_active=body.is_active,
        deposit_required=body.deposit_required,
        deposit_minor_units=body.deposit_minor_units,
    )
