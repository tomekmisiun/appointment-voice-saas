from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.service import Service
from app.services.business_service import require_business


def create_service(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    name: str,
    duration_minutes: int,
    price_minor_units: int | None = None,
    currency: str | None = None,
) -> Service:
    require_business(db, business_id, tenant_id)
    svc = Service(
        tenant_id=tenant_id,
        business_id=business_id,
        name=name,
        duration_minutes=duration_minutes,
        is_active=True,
        price_minor_units=price_minor_units,
        currency=currency,
    )
    db.add(svc)
    db.commit()
    db.refresh(svc)
    return svc


def get_service(db: Session, service_id: int, tenant_id: int) -> Service | None:
    return (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant_id)
        .first()
    )


def require_service(db: Session, service_id: int, tenant_id: int) -> Service:
    svc = get_service(db, service_id, tenant_id)
    if svc is None:
        raise NotFoundError("Service not found")
    return svc


def require_service_in_business(
    db: Session, service_id: int, business_id: int, tenant_id: int
) -> Service:
    """Like require_service(), but also rejects a service that belongs to
    a different business within the same tenant."""
    svc = require_service(db, service_id, tenant_id)
    if svc.business_id != business_id:
        raise NotFoundError("Service not found")
    return svc


def list_services(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Service]:
    query = db.query(Service).filter(
        Service.business_id == business_id, Service.tenant_id == tenant_id
    )
    if not include_inactive:
        query = query.filter(Service.is_active.is_(True))
    return query.order_by(Service.id.asc()).offset(skip).limit(limit).all()


def delete_service(
    db: Session, service_id: int, tenant_id: int, *, business_id: int
) -> None:
    from app.models.booking import Booking, BookingStatus

    svc = require_service_in_business(db, service_id, business_id, tenant_id)
    has_bookings = (
        db.query(Booking)
        .filter(
            Booking.service_id == service_id,
            Booking.status != BookingStatus.CANCELLED,
        )
        .first()
    )
    if has_bookings:
        raise ConflictError("Cannot delete a service that has confirmed bookings")
    db.delete(svc)
    db.commit()


def update_service(
    db: Session,
    service_id: int,
    business_id: int,
    tenant_id: int,
    *,
    name: str | None = None,
    duration_minutes: int | None = None,
    price_minor_units: int | None = None,
    currency: str | None = None,
    is_active: bool | None = None,
) -> Service:
    svc = require_service_in_business(db, service_id, business_id, tenant_id)
    if name is not None:
        svc.name = name
    if duration_minutes is not None:
        svc.duration_minutes = duration_minutes
    if price_minor_units is not None:
        svc.price_minor_units = price_minor_units
    if currency is not None:
        svc.currency = currency
    if is_active is not None:
        svc.is_active = is_active
    db.commit()
    db.refresh(svc)
    return svc
