import re

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.audit_log import AuditAction
from app.models.client import Client
from app.models.customer import Customer
from app.services.audit_log_service import create_audit_log
from app.services.business_service import require_business


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    return digits


def get_or_create_customer(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    phone: str,
    name: str | None = None,
) -> Customer:
    require_business(db, business_id, tenant_id)
    phone_normalized = normalize_phone(phone)
    existing = (
        db.query(Customer)
        .filter(
            Customer.business_id == business_id,
            Customer.tenant_id == tenant_id,
            Customer.phone_normalized == phone_normalized,
        )
        .first()
    )
    if existing is not None:
        return existing

    customer = Customer(
        tenant_id=tenant_id,
        business_id=business_id,
        phone=phone,
        phone_normalized=phone_normalized,
        name=name,
    )
    db.add(customer)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(Customer)
            .filter(
                Customer.business_id == business_id,
                Customer.tenant_id == tenant_id,
                Customer.phone_normalized == phone_normalized,
            )
            .first()
        )
        if existing is not None:
            return existing
        raise ConflictError("Customer with this phone already exists")
    db.refresh(customer)
    return customer


def get_customer_by_phone(
    db: Session, *, business_id: int, tenant_id: int, phone: str
) -> Customer | None:
    return (
        db.query(Customer)
        .filter(
            Customer.business_id == business_id,
            Customer.tenant_id == tenant_id,
            Customer.phone_normalized == normalize_phone(phone),
        )
        .first()
    )


def get_customer(db: Session, customer_id: int, tenant_id: int) -> Customer | None:
    return (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        .first()
    )


def require_customer(db: Session, customer_id: int, tenant_id: int) -> Customer:
    customer = get_customer(db, customer_id, tenant_id)
    if customer is None:
        raise NotFoundError("Customer not found")
    return customer


def list_customers(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[Customer]:
    return (
        db.query(Customer)
        .filter(
            Customer.business_id == business_id,
            Customer.tenant_id == tenant_id,
        )
        .order_by(Customer.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_customer(
    db: Session,
    customer_id: int,
    tenant_id: int,
    *,
    name: str | None = None,
) -> Customer:
    customer = require_customer(db, customer_id, tenant_id)
    if name is not None:
        customer.name = name
    db.commit()
    db.refresh(customer)
    return customer


def gdpr_delete_customer(
    db: Session,
    customer_id: int,
    tenant_id: int,
    *,
    actor_id: int | None = None,
) -> Customer:
    """Anonymize a customer's personal data on request. Not a hard delete:
    Booking.customer_id has no ON DELETE clause (defaults to RESTRICT), so a
    customer with any booking history can't be removed without breaking
    that constraint — and deleting the row would also break the booking and
    audit trail businesses are required to keep. Scrubs PII on the Customer
    and any linked Client (P2-001) while leaving both rows, and everything
    that references them, intact. Applies regardless of booking status —
    GDPR erasure requests aren't conditional on having no upcoming
    appointment."""
    customer = require_customer(db, customer_id, tenant_id)
    customer.name = None
    customer.phone = "deleted"
    customer.phone_normalized = f"deleted-{customer.id}"

    client = (
        db.query(Client)
        .filter(Client.tenant_id == tenant_id, Client.customer_id == customer.id)
        .first()
    )
    if client is not None:
        client.name = "Deleted client"
        client.email = None
        client.phone = None
        client.notes = None

    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.CUSTOMER_ANONYMIZED,
        source=f"customer_id={customer.id}",
        commit=False,
    )
    db.commit()
    db.refresh(customer)
    return customer
