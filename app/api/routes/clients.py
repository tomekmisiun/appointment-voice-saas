from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.client_service import (
    create_client,
    list_clients,
    require_client,
    update_client,
)

router = APIRouter(prefix="/businesses/{business_id}/clients", tags=["clients"])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client_endpoint(
    business_id: int,
    body: ClientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return create_client(
        db,
        tenant_id=current_user.tenant_id,
        business_id=business_id,
        name=body.name,
        customer_id=body.customer_id,
        email=body.email,
        phone=body.phone,
        notes=body.notes,
    )


@router.get("", response_model=list[ClientRead])
def list_clients_endpoint(
    business_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return list_clients(
        db,
        business_id,
        current_user.tenant_id,
        skip=skip,
        limit=size,
    )


@router.get("/{client_id}", response_model=ClientRead)
def get_client_endpoint(
    business_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_client(db, client_id, current_user.tenant_id)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client_endpoint(
    business_id: int,
    client_id: int,
    body: ClientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return update_client(
        db,
        client_id,
        current_user.tenant_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        notes=body.notes,
    )
