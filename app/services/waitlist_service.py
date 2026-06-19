from datetime import date, datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import NotFoundError
from app.models.waitlist_entry import WaitlistEntry, WaitlistEntryStatus
from app.services.business_service import require_business
from app.services.customer_service import require_customer
from app.services.notification_service import enqueue_send_notification_job, enqueue_waitlist_offer
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
    slot would satisfy. Entries with no staff preference (staff_id IS NULL)
    always match; entries that asked for a specific staff member only match
    if that's the staff member whose slot just opened up. Returns all
    matches, oldest first -- callers (cancel_booking()'s P2-011 offer,
    expire_stale_waitlist_offers()'s P2-012 escalation) each offer only the
    first/oldest match, leaving the rest WAITING for the next round."""
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


def expire_stale_waitlist_offers(db: Session) -> int:
    """Periodic maintenance (P2-012): expire OFFERED entries whose offer
    has been outstanding longer than settings.waitlist_offer_timeout_minutes
    -- updated_at is the offer timestamp, since the only thing that flips
    an entry to OFFERED is this status transition -- and escalate by
    offering the next eligible WAITING entry for the same business/
    service/date instead, so a non-responsive customer can't block the
    waitlist forever. Returns the number of offers expired."""
    threshold = datetime.now(timezone.utc) - timedelta(
        minutes=settings.waitlist_offer_timeout_minutes
    )
    stale_entries = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.status == WaitlistEntryStatus.OFFERED,
            WaitlistEntry.updated_at <= threshold,
        )
        .all()
    )

    if not stale_entries:
        return 0

    notification_ids: list[int] = []
    for entry in stale_entries:
        entry.status = WaitlistEntryStatus.EXPIRED
        notification_ids.extend(_escalate_to_next_waiting_entry(db, entry))

    db.commit()
    for notification_id in notification_ids:
        enqueue_send_notification_job(notification_id)
    return len(stale_entries)


def _escalate_to_next_waiting_entry(db: Session, expired_entry: WaitlistEntry) -> list[int]:
    """Re-offer the slot that expired_entry's offer was for. Matches on
    expired_entry.offered_for_staff_id (the freed slot's actual staff), not
    expired_entry.staff_id (that customer's own preference, which may be
    NULL/"any staff" even though the slot belonged to a specific staff
    member)."""
    candidates = find_matching_waitlist_entries(
        db,
        business_id=expired_entry.business_id,
        tenant_id=expired_entry.tenant_id,
        service_id=expired_entry.service_id,
        desired_date=expired_entry.desired_date,
        staff_id=expired_entry.offered_for_staff_id,
    )
    if not candidates:
        return []

    next_entry = candidates[0]
    next_entry.status = WaitlistEntryStatus.OFFERED
    next_entry.offered_for_staff_id = expired_entry.offered_for_staff_id
    business = require_business(db, next_entry.business_id, next_entry.tenant_id)
    customer = require_customer(db, next_entry.customer_id, next_entry.tenant_id)
    service = require_service(db, next_entry.service_id, next_entry.tenant_id)
    intent = enqueue_waitlist_offer(
        db, entry=next_entry, business=business, customer=customer, service=service
    )
    return [intent.id]
