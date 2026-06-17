from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.client import Client
from app.services.business_service import require_business
from app.services.customer_service import require_customer


def create_client(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    name: str,
    customer_id: int | None = None,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
) -> Client:
    require_business(db, business_id, tenant_id)
    if customer_id is not None:
        require_customer(db, customer_id, tenant_id)
        existing = (
            db.query(Client)
            .filter(Client.business_id == business_id, Client.customer_id == customer_id)
            .first()
        )
        if existing is not None:
            raise ConflictError("A client profile already exists for this customer")

    client = Client(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        name=name,
        email=email,
        phone=phone,
        notes=notes,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get_client(db: Session, client_id: int, tenant_id: int) -> Client | None:
    return (
        db.query(Client)
        .filter(Client.id == client_id, Client.tenant_id == tenant_id)
        .first()
    )


def require_client(db: Session, client_id: int, tenant_id: int) -> Client:
    client = get_client(db, client_id, tenant_id)
    if client is None:
        raise NotFoundError("Client not found")
    return client


def list_clients(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Client]:
    return (
        db.query(Client)
        .filter(Client.business_id == business_id, Client.tenant_id == tenant_id)
        .order_by(Client.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_client(
    db: Session,
    client_id: int,
    tenant_id: int,
    *,
    name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
) -> Client:
    client = require_client(db, client_id, tenant_id)
    if name is not None:
        client.name = name
    if email is not None:
        client.email = email
    if phone is not None:
        client.phone = phone
    if notes is not None:
        client.notes = notes
    db.commit()
    db.refresh(client)
    return client
