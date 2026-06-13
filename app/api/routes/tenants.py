from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import require_permission
from app.api.openapi import ADMIN_ERROR_RESPONSES
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.tenant import TenantCreate, TenantRead, TenantUpdate
from app.services.tenant_service import (
    get_tenant_by_id,
    list_tenants,
    provision_tenant,
    set_tenant_active_state,
    update_tenant,
)

router = APIRouter(prefix="/admin/tenants", tags=["admin", "tenants"])


@router.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    summary="Provision a new tenant",
    responses=ADMIN_ERROR_RESPONSES,
)
def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_PROVISION)),
):
    return provision_tenant(
        db,
        slug=tenant_data.slug,
        name=tenant_data.name,
        admin_id=current_user.id,
        admin_tenant_id=current_user.tenant_id,
    )


@router.get(
    "",
    response_model=list[TenantRead],
    summary="List tenants",
    responses=ADMIN_ERROR_RESPONSES,
)
def list_tenant_records(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_LIST)),
):
    skip = (page - 1) * size

    return list_tenants(
        db,
        skip=skip,
        limit=size,
        include_inactive=include_inactive,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantRead,
    summary="Get tenant details",
    responses=ADMIN_ERROR_RESPONSES,
)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_LIST)),
):
    tenant = get_tenant_by_id(db, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


@router.patch(
    "/{tenant_id}",
    response_model=TenantRead,
    summary="Update tenant metadata or lifecycle state",
    responses=ADMIN_ERROR_RESPONSES,
)
def patch_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_MANAGE)),
):
    if tenant_update.is_active is None and tenant_update.name is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided",
        )

    tenant = get_tenant_by_id(db, tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if tenant_update.name is not None:
        tenant = update_tenant(db, tenant_id, name=tenant_update.name)

    if tenant_update.is_active is not None:
        tenant = set_tenant_active_state(
            db,
            tenant_id=tenant_id,
            is_active=tenant_update.is_active,
            admin_id=current_user.id,
            admin_tenant_id=current_user.tenant_id,
        )

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant
