from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user, require_demo_business_access, require_non_demo_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.booking import BookingRead
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.services.client_service import (
    create_client,
    get_bookings_for_client,
    list_clients,
    require_client_in_business,
    update_client,
)

router = APIRouter(
    prefix="/businesses/{business_id}/clients",
    tags=["clients"],
    dependencies=[Depends(require_demo_business_access)],
)

_MASKED_PHONE = "***"
_MASKED_EMAIL = "***@***.***"


def _mask_client(client: ClientRead, is_demo: bool) -> ClientRead:
    if not is_demo:
        return client
    return client.model_copy(
        update={
            "phone": _MASKED_PHONE if client.phone else client.phone,
            "email": _MASKED_EMAIL if client.email else client.email,
        }
    )


@router.post(
    "",
    response_model=ClientRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_non_demo_user)],
)
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
    rows = list_clients(db, business_id, current_user.tenant_id, skip=skip, limit=size)
    parsed = [ClientRead.model_validate(r) for r in rows]
    return [_mask_client(c, current_user.is_demo_user) for c in parsed]


@router.get("/{client_id}", response_model=ClientRead)
def get_client_endpoint(
    business_id: int,
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = require_client_in_business(db, client_id, business_id, current_user.tenant_id)
    return _mask_client(ClientRead.model_validate(row), current_user.is_demo_user)


@router.get("/{client_id}/bookings", response_model=list[BookingRead])
def get_client_bookings_endpoint(
    business_id: int,
    client_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skip = (page - 1) * size
    return get_bookings_for_client(
        db,
        client_id,
        business_id,
        current_user.tenant_id,
        skip=skip,
        limit=size,
    )


@router.patch(
    "/{client_id}",
    response_model=ClientRead,
    dependencies=[Depends(require_non_demo_user)],
)
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
        business_id,
        current_user.tenant_id,
        name=body.name,
        email=body.email,
        phone=body.phone,
        notes=body.notes,
    )
