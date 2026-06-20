from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.audit_log import AuditAction
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.booking_line_item import BookingLineItem
from app.models.waitlist_entry import WaitlistEntryStatus
from app.services.audit_log_service import create_audit_log
from app.services.business_service import require_business
from app.services.customer_service import require_customer_in_business
from app.services.calendar_service import (
    enqueue_calendar_event,
    enqueue_cancel_calendar_event_job,
    enqueue_sync_calendar_event_job,
    get_calendar_event_for_booking,
)
from app.services.notification_service import (
    enqueue_booking_cancellation,
    enqueue_booking_confirmation,
    enqueue_send_notification_job,
    enqueue_waitlist_offer,
)
from app.services.service_service import require_service, require_service_in_business
from app.services.staff_service import require_staff_in_business
from app.services.waitlist_service import find_matching_waitlist_entries


def _check_double_booking(
    db: Session,
    *,
    staff_id: int | None,
    business_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_booking_id: int | None = None,
) -> None:
    if staff_id is None:
        return
    query = (
        db.query(Booking)
        .filter(
            Booking.staff_id == staff_id,
            Booking.business_id == business_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at < ends_at,
            Booking.ends_at > starts_at,
        )
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    conflict = query.first()
    if conflict is not None:
        raise ConflictError("This time slot is already booked for the selected staff")


def create_booking(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    customer_id: int,
    service_id: int,
    staff_id: int | None,
    starts_at: datetime,
    source: str = BookingSource.API,
    actor_id: int | None = None,
) -> Booking:
    business = require_business(db, business_id, tenant_id)
    customer = require_customer_in_business(db, customer_id, business_id, tenant_id)
    svc = require_service_in_business(db, service_id, business_id, tenant_id)
    if staff_id is not None:
        require_staff_in_business(db, staff_id, business_id, tenant_id)

    ends_at = starts_at + timedelta(minutes=svc.duration_minutes)

    _check_double_booking(
        db,
        staff_id=staff_id,
        business_id=business_id,
        starts_at=starts_at,
        ends_at=ends_at,
    )

    booking = Booking(
        tenant_id=tenant_id,
        business_id=business_id,
        customer_id=customer_id,
        service_id=service_id,
        staff_id=staff_id,
        starts_at=starts_at,
        ends_at=ends_at,
        status=BookingStatus.CONFIRMED,
        source=source,
    )
    db.add(booking)
    db.flush()
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.BOOKING_CREATED,
        target_booking_id=booking.id,
        source=source,
        commit=False,
    )
    confirmation_intents = enqueue_booking_confirmation(
        db,
        booking=booking,
        business=business,
        customer=customer,
        service=svc,
    )
    confirmation_intent_ids = [intent.id for intent in confirmation_intents]
    try:
        calendar_event = enqueue_calendar_event(db, booking=booking, business=business)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "no_overlapping_staff_bookings" in str(exc.orig):
            raise ConflictError("This time slot is already booked for the selected staff")
        raise
    db.refresh(booking)
    for notification_id in confirmation_intent_ids:
        enqueue_send_notification_job(notification_id)
    enqueue_sync_calendar_event_job(calendar_event.id)
    return booking


def get_next_confirmed_booking(
    db: Session, *, business_id: int, tenant_id: int, customer_id: int
) -> Booking | None:
    return (
        db.query(Booking)
        .filter(
            Booking.business_id == business_id,
            Booking.tenant_id == tenant_id,
            Booking.customer_id == customer_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.starts_at > datetime.now(timezone.utc),
        )
        .order_by(Booking.starts_at.asc())
        .first()
    )


def get_last_staff_booking(
    db: Session, *, business_id: int, tenant_id: int, customer_id: int
) -> Booking | None:
    """Most recent booking (any status) with a staff member assigned, used
    to suggest reusing the same staff member on a future visit."""
    return (
        db.query(Booking)
        .filter(
            Booking.business_id == business_id,
            Booking.tenant_id == tenant_id,
            Booking.customer_id == customer_id,
            Booking.staff_id.isnot(None),
        )
        .order_by(Booking.starts_at.desc())
        .first()
    )


def get_booking(db: Session, booking_id: int, tenant_id: int) -> Booking | None:
    return (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.tenant_id == tenant_id)
        .first()
    )


def require_booking(db: Session, booking_id: int, tenant_id: int) -> Booking:
    booking = get_booking(db, booking_id, tenant_id)
    if booking is None:
        raise NotFoundError("Booking not found")
    return booking


def require_booking_in_business(
    db: Session, booking_id: int, business_id: int, tenant_id: int
) -> Booking:
    """Like require_booking(), but also rejects a booking that belongs to
    a different business within the same tenant."""
    booking = require_booking(db, booking_id, tenant_id)
    if booking.business_id != business_id:
        raise NotFoundError("Booking not found")
    return booking


def add_booking_line_item(
    db: Session, *, booking_id: int, tenant_id: int, service_id: int
) -> BookingLineItem:
    """Append an additional service to a booking (P2-008). Booking.service_id
    stays the booking's primary/first service for all existing
    single-service code paths; line items are purely additive and not yet
    consulted by availability search or the IVR (P2-009)."""
    booking = require_booking(db, booking_id, tenant_id)
    svc = require_service(db, service_id, tenant_id)
    if svc.business_id != booking.business_id:
        raise NotFoundError("Service not found")

    next_position = (
        db.query(BookingLineItem)
        .filter(BookingLineItem.booking_id == booking_id)
        .count()
    )
    line_item = BookingLineItem(
        tenant_id=tenant_id,
        business_id=booking.business_id,
        booking_id=booking_id,
        service_id=service_id,
        position=next_position,
        duration_minutes=svc.duration_minutes,
    )
    db.add(line_item)
    db.commit()
    db.refresh(line_item)
    return line_item


def list_booking_line_items(
    db: Session, booking_id: int, tenant_id: int
) -> list[BookingLineItem]:
    require_booking(db, booking_id, tenant_id)
    return (
        db.query(BookingLineItem)
        .filter(BookingLineItem.booking_id == booking_id, BookingLineItem.tenant_id == tenant_id)
        .order_by(BookingLineItem.position.asc())
        .all()
    )


def get_booking_total_duration_minutes(db: Session, booking_id: int, tenant_id: int) -> int:
    """Sum of duration_minutes across this booking's line items. Returns 0
    if no line items have been added (single-service bookings derive their
    duration from Booking.ends_at - Booking.starts_at instead)."""
    line_items = list_booking_line_items(db, booking_id, tenant_id)
    return sum(item.duration_minutes for item in line_items)


def list_bookings(
    db: Session,
    business_id: int,
    tenant_id: int,
    *,
    status: str | None = None,
    staff_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Booking]:
    query = db.query(Booking).filter(
        Booking.business_id == business_id,
        Booking.tenant_id == tenant_id,
    )
    if status is not None:
        query = query.filter(Booking.status == status)
    if staff_id is not None:
        query = query.filter(Booking.staff_id == staff_id)
    return (
        query.order_by(Booking.starts_at.asc()).offset(skip).limit(limit).all()
    )


def cancel_booking(
    db: Session,
    booking_id: int,
    business_id: int,
    tenant_id: int,
    *,
    reason: str | None = None,
    actor_id: int | None = None,
) -> Booking:
    booking = require_booking_in_business(db, booking_id, business_id, tenant_id)
    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError("Booking is already cancelled")
    booking.status = BookingStatus.CANCELLED
    booking.cancel_reason = reason
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.BOOKING_CANCELLED,
        target_booking_id=booking.id,
        source=booking.source,
        commit=False,
    )
    business = require_business(db, booking.business_id, tenant_id)
    customer = require_customer_in_business(db, booking.customer_id, booking.business_id, tenant_id)
    service = require_service_in_business(db, booking.service_id, booking.business_id, tenant_id)
    cancellation_intents = enqueue_booking_cancellation(
        db,
        booking=booking,
        business=business,
        customer=customer,
        service=service,
    )
    cancellation_intent_ids = [intent.id for intent in cancellation_intents]

    matching_entries = find_matching_waitlist_entries(
        db,
        business_id=booking.business_id,
        tenant_id=tenant_id,
        service_id=booking.service_id,
        desired_date=booking.starts_at.date(),
        staff_id=booking.staff_id,
        for_update=True,
    )
    waitlist_notification_ids = []
    if matching_entries:
        entry = matching_entries[0]
        entry.status = WaitlistEntryStatus.OFFERED
        entry.offered_for_staff_id = booking.staff_id
        waitlist_customer = require_customer_in_business(
            db, entry.customer_id, entry.business_id, tenant_id
        )
        offer_intent = enqueue_waitlist_offer(
            db, entry=entry, business=business, customer=waitlist_customer, service=service,
        )
        waitlist_notification_ids.append(offer_intent.id)

    cal_event = get_calendar_event_for_booking(db, booking.id, tenant_id)
    db.commit()
    db.refresh(booking)
    for notification_id in cancellation_intent_ids:
        enqueue_send_notification_job(notification_id)
    for notification_id in waitlist_notification_ids:
        enqueue_send_notification_job(notification_id)
    if cal_event is not None:
        enqueue_cancel_calendar_event_job(cal_event.id)
    return booking


def reschedule_booking(
    db: Session,
    booking_id: int,
    business_id: int,
    tenant_id: int,
    *,
    new_starts_at: datetime,
    reason: str | None = None,
    actor_id: int | None = None,
    source: str = BookingSource.API,
) -> Booking:
    """Reschedule by cancelling the existing booking and creating a new one
    at the new time, with the same service/staff/customer. Not an in-place
    time update: the calendar adapter only supports create/cancel for an
    event, not updating an already-synced event's time, so cancel+create is
    the only way to get the calendar in sync with the new time. This reuses
    cancel_booking()/create_booking() as-is, so notifications and calendar
    sync keep working unchanged — the tradeoff is the booking gets a new id
    and the customer gets both a cancellation and a new confirmation
    notification. On top of the cancel/create audit entries those calls
    already log, this also logs a single BOOKING_RESCHEDULED entry on the
    new booking (source records the old booking id) so the pair reads as a
    reschedule rather than two unrelated events."""
    old_booking = require_booking_in_business(db, booking_id, business_id, tenant_id)
    cancel_booking(db, old_booking.id, business_id, tenant_id, reason=reason, actor_id=actor_id)
    new_booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=old_booking.business_id,
        customer_id=old_booking.customer_id,
        service_id=old_booking.service_id,
        staff_id=old_booking.staff_id,
        starts_at=new_starts_at,
        source=source,
        actor_id=actor_id,
    )
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.BOOKING_RESCHEDULED,
        target_booking_id=new_booking.id,
        source=f"rescheduled_from_booking_{old_booking.id}",
    )
    return new_booking
