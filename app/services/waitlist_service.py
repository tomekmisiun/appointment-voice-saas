from datetime import date

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.waitlist_entry import WaitlistEntry, WaitlistEntryStatus
from app.services.business_service import require_business
from app.services.customer_service import require_customer
from app.services.service_service import require_service
from app.services.staff_service import require_staff


def create_waitlist_entry(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    customer_id: int,
    service_id: int,
    desired_date: date,
    staff_id: int | None = None,
) -> WaitlistEntry:
    require_business(db, business_id, tenant_id)
    customer = require_customer(db, customer_id, tenant_id)
    if customer.business_id != business_id:
        raise NotFoundError("Customer not found")
    svc = require_service(db, service_id, tenant_id)
    if svc.business_id != business_id:
        raise NotFoundError("Service not found")
    if staff_id is not None:
        staff = require_staff(db, staff_id, tenant_id)
        if staff.business_id != business_id:
            raise NotFoundError("Staff member not found")

    entry = WaitlistEntry(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        service_id=service_id,
        staff_id=staff_id,
        desired_date=desired_date,
        status=WaitlistEntryStatus.WAITING,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_waitlist_entry(db: Session, entry_id: int, tenant_id: int) -> WaitlistEntry | None:
    return (
        db.query(WaitlistEntry)
        .filter(WaitlistEntry.id == entry_id, WaitlistEntry.tenant_id == tenant_id)
        .first()
    )


def require_waitlist_entry(db: Session, entry_id: int, tenant_id: int) -> WaitlistEntry:
    entry = get_waitlist_entry(db, entry_id, tenant_id)
    if entry is None:
        raise NotFoundError("Waitlist entry not found")
    return entry


def list_waitlist_entries(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    status: str | None = None,
    service_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[WaitlistEntry]:
    query = db.query(WaitlistEntry).filter(
        WaitlistEntry.business_id == business_id,
        WaitlistEntry.tenant_id == tenant_id,
    )
    if status is not None:
        query = query.filter(WaitlistEntry.status == status)
    if service_id is not None:
        query = query.filter(WaitlistEntry.service_id == service_id)
    return (
        query.order_by(WaitlistEntry.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def find_matching_waitlist_entries(
    db: Session,
    *,
    business_id: int,
    tenant_id: int,
    service_id: int,
    desired_date: date,
    staff_id: int | None = None,
) -> list[WaitlistEntry]:
    """WAITING entries for this business/service/date that a newly freed
    slot would satisfy (P2-011, triggered from cancel_booking()). Entries
    with no staff preference (staff_id IS NULL) always match; entries that
    asked for a specific staff member only match if that's the staff
    member whose slot just opened up. Returns all matches, oldest first --
    picking a single winner and expiring the rest is P2-012's job."""
    query = db.query(WaitlistEntry).filter(
        WaitlistEntry.business_id == business_id,
        WaitlistEntry.tenant_id == tenant_id,
        WaitlistEntry.service_id == service_id,
        WaitlistEntry.desired_date == desired_date,
        WaitlistEntry.status == WaitlistEntryStatus.WAITING,
    )
    if staff_id is not None:
        query = query.filter(
            or_(WaitlistEntry.staff_id.is_(None), WaitlistEntry.staff_id == staff_id)
        )
    else:
        query = query.filter(WaitlistEntry.staff_id.is_(None))
    return query.order_by(WaitlistEntry.created_at.asc()).all()


def update_waitlist_entry_status(
    db: Session, entry_id: int, tenant_id: int, *, status: str
) -> WaitlistEntry:
    entry = require_waitlist_entry(db, entry_id, tenant_id)
    entry.status = status
    db.commit()
    db.refresh(entry)
    return entry
