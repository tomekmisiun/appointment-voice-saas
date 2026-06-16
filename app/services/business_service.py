from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.business import Business


def create_business(
    db: Session,
    *,
    tenant_id: int,
    name: str,
    timezone: str,
    phone: str | None = None,
    transfer_enabled: bool = False,
    transfer_destination_policy: str = "business_phone",
) -> Business:
    business = Business(
        tenant_id=tenant_id,
        name=name,
        timezone=timezone,
        phone=phone,
        is_active=True,
        transfer_enabled=transfer_enabled,
        transfer_destination_policy=transfer_destination_policy,
    )
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def get_business(db: Session, business_id: int, tenant_id: int) -> Business | None:
    return (
        db.query(Business)
        .filter(Business.id == business_id, Business.tenant_id == tenant_id)
        .first()
    )


def require_business(db: Session, business_id: int, tenant_id: int) -> Business:
    business = get_business(db, business_id, tenant_id)
    if business is None:
        raise NotFoundError("Business not found")
    return business


def get_business_global(db: Session, business_id: int) -> Business | None:
    """Return a business by id without tenant filter (for public webhook endpoints)."""
    return db.query(Business).filter(Business.id == business_id).first()


def list_businesses(
    db: Session,
    tenant_id: int,
    *,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Business]:
    query = db.query(Business).filter(Business.tenant_id == tenant_id)
    if not include_inactive:
        query = query.filter(Business.is_active.is_(True))
    return query.order_by(Business.id.asc()).offset(skip).limit(limit).all()


def update_business(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    name: str | None = None,
    timezone: str | None = None,
    phone: str | None = None,
    is_active: bool | None = None,
    transfer_enabled: bool | None = None,
    transfer_destination_policy: str | None = None,
) -> Business:
    business = require_business(db, business_id, tenant_id)
    if name is not None:
        business.name = name
    if timezone is not None:
        business.timezone = timezone
    if phone is not None:
        business.phone = phone
    if is_active is not None:
        business.is_active = is_active
    if transfer_enabled is not None:
        business.transfer_enabled = transfer_enabled
    if transfer_destination_policy is not None:
        business.transfer_destination_policy = transfer_destination_policy
    db.commit()
    db.refresh(business)
    return business
