from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.staff import Staff
from app.services.business_service import require_business


def create_staff(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    name: str,
    phone: str | None = None,
) -> Staff:
    require_business(db, business_id, tenant_id)
    member = Staff(
        tenant_id=tenant_id,
        business_id=business_id,
        name=name,
        phone=phone,
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
    is_active: bool | None = None,
) -> Staff:
    member = require_staff_in_business(db, staff_id, business_id, tenant_id)
    if name is not None:
        member.name = name
    if phone is not None:
        member.phone = phone
    if is_active is not None:
        member.is_active = is_active
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
    """Return active staff members with a non-blank phone who can receive a transferred call."""
    return (
        db.query(Staff)
        .filter(
            Staff.business_id == business_id,
            Staff.tenant_id == tenant_id,
            Staff.is_active.is_(True),
            Staff.phone.isnot(None),
            func.trim(Staff.phone) != "",
        )
        .order_by(Staff.id.asc())
        .limit(limit)
        .all()
    )
