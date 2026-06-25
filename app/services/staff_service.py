from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.audit_log import AuditAction
from app.models.staff import Staff
from app.services.audit_log_service import create_audit_log
from app.services.business_service import require_business


def create_staff(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    name: str,
    phone: str | None = None,
    contact_email: str | None = None,
    position: str | None = None,
    accepts_bookings: bool = True,
    is_customer_visible: bool = True,
) -> Staff:
    require_business(db, business_id, tenant_id)
    member = Staff(
        tenant_id=tenant_id,
        business_id=business_id,
        name=name,
        phone=phone,
        contact_email=contact_email,
        position=position,
        accepts_bookings=accepts_bookings,
        is_customer_visible=is_customer_visible,
        is_active=True,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def get_staff(db: Session, staff_id: int, tenant_id: int) -> Staff | None:
    return (
        db.query(Staff)
        .filter(Staff.id == staff_id, Staff.tenant_id == tenant_id)
        .first()
    )


def require_staff(db: Session, staff_id: int, tenant_id: int) -> Staff:
    member = get_staff(db, staff_id, tenant_id)
    if member is None:
        raise NotFoundError("Staff member not found")
    return member


def require_staff_in_business(
    db: Session, staff_id: int, business_id: int, tenant_id: int
) -> Staff:
    """Like require_staff(), but also rejects a staff member that belongs
    to a different business within the same tenant."""
    member = require_staff(db, staff_id, tenant_id)
    if member.business_id != business_id:
        raise NotFoundError("Staff member not found")
    return member


def list_staff(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[Staff]:
    query = db.query(Staff).filter(
        Staff.business_id == business_id, Staff.tenant_id == tenant_id
    )
    if not include_inactive:
        query = query.filter(Staff.is_active.is_(True))
    return query.order_by(Staff.id.asc()).offset(skip).limit(limit).all()


def update_staff(
    db: Session,
    staff_id: int,
    business_id: int,
    tenant_id: int,
    *,
    name: str | None = None,
    phone: str | None = None,
    contact_email: str | None = None,
    position: str | None = None,
    accepts_bookings: bool | None = None,
    is_customer_visible: bool | None = None,
    # Legacy param kept for internal callers (IVR tests etc.).
    # Use deactivate_staff / reactivate_staff from the API layer instead.
    is_active: bool | None = None,
    # Fields passed from the route handler that should always be applied,
    # even when the value is None (to allow clearing nullable columns).
    _always_set: dict | None = None,
) -> Staff:
    member = require_staff_in_business(db, staff_id, business_id, tenant_id)

    # Apply kwargs passed via the route handler's model_fields_set path.
    # These are applied unconditionally so null values clear the column.
    if _always_set:
        for field, value in _always_set.items():
            setattr(member, field, value)
    else:
        # Keyword-arg path (internal callers): skip None to leave fields untouched.
        if name is not None:
            member.name = name
        if phone is not None:
            member.phone = phone
        if contact_email is not None:
            member.contact_email = contact_email
        if position is not None:
            member.position = position
        if accepts_bookings is not None:
            member.accepts_bookings = accepts_bookings
        if is_customer_visible is not None:
            member.is_customer_visible = is_customer_visible
        if is_active is not None:
            member.is_active = is_active

    db.commit()
    db.refresh(member)
    return member


def deactivate_staff(
    db: Session,
    staff_id: int,
    business_id: int,
    tenant_id: int,
    *,
    actor_id: int,
) -> Staff:
    """Soft-deactivate a staff member and emit an audit log entry.

    History-safe: does not remove the staff row or its booking history.
    The staff member remains queryable via include_inactive=True."""
    member = require_staff_in_business(db, staff_id, business_id, tenant_id)
    member.is_active = False
    db.flush()
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.STAFF_DEACTIVATED,
        target_staff_id=staff_id,
        commit=False,
    )
    db.commit()
    db.refresh(member)
    return member


def reactivate_staff(
    db: Session,
    staff_id: int,
    business_id: int,
    tenant_id: int,
    *,
    actor_id: int,
) -> Staff:
    """Re-activate a previously deactivated staff member."""
    member = require_staff_in_business(db, staff_id, business_id, tenant_id)
    member.is_active = True
    db.flush()
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.STAFF_REACTIVATED,
        target_staff_id=staff_id,
        commit=False,
    )
    db.commit()
    db.refresh(member)
    return member


def get_eligible_transfer_staff(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    limit: int = 50,
) -> list[Staff]:
    """Return active, booking-eligible staff members with a non-blank phone
    who can receive a transferred call."""
    return (
        db.query(Staff)
        .filter(
            Staff.business_id == business_id,
            Staff.tenant_id == tenant_id,
            Staff.is_active.is_(True),
            Staff.accepts_bookings.is_(True),
            Staff.phone.isnot(None),
            func.trim(Staff.phone) != "",
        )
        .order_by(Staff.id.asc())
        .limit(limit)
        .all()
    )
