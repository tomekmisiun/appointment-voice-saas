from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessRead, BusinessUpdate
from app.services.business_service import (
    create_business,
    list_businesses,
    require_business,
    update_business,
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessRead, status_code=status.HTTP_201_CREATED)
def create_business_endpoint(
    body: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return create_business(
        db,
        tenant_id=current_user.tenant_id,
        name=body.name,
        timezone=body.timezone,
        phone=body.phone,
    )


@router.get("", response_model=list[BusinessRead])
def list_businesses_endpoint(
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return list_businesses(
        db,
        current_user.tenant_id,
        include_inactive=include_inactive,
        skip=skip,
        limit=size,
    )


@router.get("/{business_id}", response_model=BusinessRead)
def get_business_endpoint(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_business(db, business_id, current_user.tenant_id)


@router.patch("/{business_id}", response_model=BusinessRead)
def update_business_endpoint(
    business_id: int,
    body: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return update_business(
        db,
        business_id,
        current_user.tenant_id,
        name=body.name,
        timezone=body.timezone,
        phone=body.phone,
        is_active=body.is_active,
    )
