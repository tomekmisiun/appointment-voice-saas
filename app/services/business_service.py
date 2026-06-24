from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.business import Business


def create_business(
    db: Session,
    *,
    tenant_id: int,
    name: str,
    timezone: str,
    language: str = "en",
    phone: str | None = None,
    transfer_enabled: bool = False,
    transfer_destination_policy: str = "business_phone",
    booking_mode: str = "internal_booking",
    external_booking_url: str | None = None,
    external_booking_label: str | None = None,
    external_booking_provider: str | None = None,
    subscription_plan: str = "full_booking",
) -> Business:
    business = Business(
        tenant_id=tenant_id,
        name=name,
        timezone=timezone,
        language=language,
        phone=phone,
        is_active=True,
        transfer_enabled=transfer_enabled,
        transfer_destination_policy=transfer_destination_policy,
        booking_mode=booking_mode,
        external_booking_url=external_booking_url,
        external_booking_label=external_booking_label,
        external_booking_provider=external_booking_provider,
        subscription_plan=subscription_plan,
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
    language: str | None = None,
    phone: str | None = None,
    is_active: bool | None = None,
    transfer_enabled: bool | None = None,
    transfer_destination_policy: str | None = None,
    booking_mode: str | None = None,
    external_booking_url: str | None = None,
    external_booking_label: str | None = None,
    external_booking_provider: str | None = None,
    subscription_plan: str | None = None,
) -> Business:
    business = require_business(db, business_id, tenant_id)
    if name is not None:
        business.name = name
    if timezone is not None:
        business.timezone = timezone
    if language is not None:
        business.language = language
    if phone is not None:
        business.phone = phone
    if is_active is not None:
        business.is_active = is_active
    if transfer_enabled is not None:
        business.transfer_enabled = transfer_enabled
    if transfer_destination_policy is not None:
        business.transfer_destination_policy = transfer_destination_policy
    if booking_mode is not None:
        business.booking_mode = booking_mode
    if external_booking_url is not None:
        business.external_booking_url = external_booking_url
    if external_booking_label is not None:
        business.external_booking_label = external_booking_label
    if external_booking_provider is not None:
        business.external_booking_provider = external_booking_provider
    if subscription_plan is not None:
        business.subscription_plan = subscription_plan
    db.commit()
    db.refresh(business)
    return business
