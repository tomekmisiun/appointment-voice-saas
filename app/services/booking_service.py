from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.domain_errors import BadRequestError, ConflictError, NotFoundError
from app.models.audit_log import AuditAction
from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.booking_line_item import BookingLineItem
from app.models.booking_payment import BookingPayment, BookingPaymentStatus
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
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING_PAYMENT]),
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
    override: bool = False,
    reason: str | None = None,
) -> Booking:
    if override and not (reason or "").strip():
        raise BadRequestError("reason is required for an admin override booking")
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
        action=AuditAction.BOOKING_OVERRIDE_CREATED if override else AuditAction.BOOKING_CREATED,
        target_booking_id=booking.id,
        source=reason if override else source,
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


def _fail_linked_pending_payment(db: Session, booking: Booking) -> None:
    """If `booking` has a still-PENDING BookingPayment, mark it FAILED.
    Called from both expire_pending_payment_hold() and cancel_booking() so a
    payment row can't stay PENDING forever once its booking is dead,
    regardless of which path killed the hold (auto-expiry vs. an admin
    cancelling it directly). No-op for a normal CONFIRMED-booking
    cancellation, since no BookingPayment row exists for those."""
    payment = (
        db.query(BookingPayment)
        .filter(
            BookingPayment.booking_id == booking.id,
            BookingPayment.tenant_id == booking.tenant_id,
            BookingPayment.status == BookingPaymentStatus.PENDING,
        )
        .first()
    )
    if payment is not None:
        payment.status = BookingPaymentStatus.FAILED
        payment.failure_reason = booking.cancel_reason


def create_pending_payment_hold(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    customer_id: int,
    service_id: int,
    staff_id: int | None,
    starts_at: datetime,
    provider: str,
    provider_session_id: str | None = None,
    source: str = BookingSource.API,
) -> Booking:
    """Create a Booking in PENDING_PAYMENT, reserving the slot, plus its
    linked BookingPayment row (ADR 0004 SS2/SS3). Deliberately does not call
    create_booking(): that function unconditionally fires the confirmation
    SMS and calendar sync, which must not happen until the payment actually
    succeeds (confirm_booking_payment(), below) -- a customer who never
    completes payment must not receive a "your appointment is confirmed"
    SMS for an appointment that will be cancelled minutes later."""
    require_business(db, business_id, tenant_id)
    require_customer_in_business(db, customer_id, business_id, tenant_id)
    svc = require_service_in_business(db, service_id, business_id, tenant_id)
    if not svc.deposit_required or svc.deposit_minor_units is None or svc.currency is None:
        raise BadRequestError("service does not require a deposit")
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
        status=BookingStatus.PENDING_PAYMENT,
        source=source,
    )
    # The Booking insert's own flush is inside this try block (not a
    # separate, unguarded flush before it): the no_overlapping_staff_bookings
    # exclusion constraint is checked immediately at INSERT time, not
    # deferred to commit, so a genuine concurrent-race conflict slipping
    # past _check_double_booking() above would otherwise raise a raw,
    # uncaught IntegrityError here instead of the intended ConflictError --
    # caught by cross-provider review.
    try:
        db.add(booking)
        db.flush()

        payment = BookingPayment(
            tenant_id=tenant_id,
            business_id=business_id,
            booking_id=booking.id,
            provider=provider,
            provider_session_id=provider_session_id,
            amount_minor_units=svc.deposit_minor_units,
            currency=svc.currency,
        )
        db.add(payment)
        create_audit_log(
            db,
            tenant_id=tenant_id,
            admin_id=None,
            action=AuditAction.BOOKING_CREATED,
            target_booking_id=booking.id,
            source=f"payment_hold:{provider}",
            commit=False,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if "no_overlapping_staff_bookings" in str(exc.orig):
            raise ConflictError("This time slot is already booked for the selected staff")
        raise
    db.refresh(booking)
    return booking


def confirm_booking_payment(
    db: Session,
    booking_id: int,
    business_id: int,
    tenant_id: int,
    *,
    provider_payment_id: str | None = None,
    source: str = "stripe_webhook",
) -> Booking:
    """Transition a PENDING_PAYMENT booking to CONFIRMED on successful
    payment (ADR 0004 SS5). This is the first point the confirmation SMS and
    calendar sync fire for this booking -- they were deliberately skipped at
    create_pending_payment_hold() time. Reuses the existing
    AuditAction.BOOKING_CONFIRMED (already logged elsewhere for SMS-reply
    confirmations with source="sms_reply"); `source` disambiguates which
    path confirmed it, the same way BOOKING_CREATED/BOOKING_CANCELLED
    already distinguish api/ivr/an override reason.

    Idempotent for a duplicate success event on an already-confirmed
    payment: this is the function P3-007's Stripe webhook handler will
    call, and payment providers commonly redeliver/retry success events --
    a second delivery for the same payment must be a silent no-op, not a
    ConflictError or a second round of confirmation SMS/calendar sync.
    Caught by cross-provider review."""
    booking = _require_booking_in_business_for_update(db, booking_id, business_id, tenant_id)

    if booking.status == BookingStatus.CONFIRMED:
        payment = (
            db.query(BookingPayment)
            .filter(BookingPayment.booking_id == booking.id, BookingPayment.tenant_id == tenant_id)
            .first()
        )
        if payment is not None and payment.status == BookingPaymentStatus.SUCCEEDED:
            return booking
        raise ConflictError("Booking is not awaiting payment")

    if booking.status != BookingStatus.PENDING_PAYMENT:
        raise ConflictError("Booking is not awaiting payment")

    payment = (
        db.query(BookingPayment)
        .filter(BookingPayment.booking_id == booking.id, BookingPayment.tenant_id == tenant_id)
        .first()
    )
    if payment is None:
        raise NotFoundError("No payment found for this booking")
    if payment.status != BookingPaymentStatus.PENDING:
        raise ConflictError("Payment is not pending")

    payment.status = BookingPaymentStatus.SUCCEEDED
    payment.provider_payment_id = provider_payment_id
    payment.paid_at = datetime.now(timezone.utc)

    booking.status = BookingStatus.CONFIRMED
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=None,
        action=AuditAction.BOOKING_CONFIRMED,
        target_booking_id=booking.id,
        source=source,
        commit=False,
    )

    business = require_business(db, booking.business_id, tenant_id)
    customer = require_customer_in_business(db, booking.customer_id, booking.business_id, tenant_id)
    svc = require_service_in_business(db, booking.service_id, booking.business_id, tenant_id)
    confirmation_intents = enqueue_booking_confirmation(
        db, booking=booking, business=business, customer=customer, service=svc,
    )
    confirmation_intent_ids = [intent.id for intent in confirmation_intents]
    calendar_event = enqueue_calendar_event(db, booking=booking, business=business)
    db.commit()
    db.refresh(booking)
    for notification_id in confirmation_intent_ids:
        enqueue_send_notification_job(notification_id)
    enqueue_sync_calendar_event_job(calendar_event.id)
    return booking


def expire_pending_payment_hold(
    db: Session, booking_id: int, business_id: int, tenant_id: int
) -> Booking:
    """Transition an abandoned PENDING_PAYMENT booking to CANCELLED, freeing
    the slot (ADR 0004 SS4). Deliberately not a call to cancel_booking() as-is:
    no customer-facing cancellation SMS fires (the customer never had a
    confirmed appointment, only an abandoned checkout), and this logs a
    distinct BOOKING_HOLD_EXPIRED audit action instead of BOOKING_CANCELLED
    -- but the freed slot still gets escalated to the waitlist, same as a
    real cancellation, since the slot being free is just as real."""
    booking = _require_booking_in_business_for_update(db, booking_id, business_id, tenant_id)
    if booking.status != BookingStatus.PENDING_PAYMENT:
        raise ConflictError("Booking is not a pending payment hold")

    booking.status = BookingStatus.CANCELLED
    booking.cancel_reason = "payment_hold_expired"
    _fail_linked_pending_payment(db, booking)
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=None,
        action=AuditAction.BOOKING_HOLD_EXPIRED,
        target_booking_id=booking.id,
        source="payment_hold_expired",
        commit=False,
    )

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
        business = require_business(db, booking.business_id, tenant_id)
        service = require_service_in_business(db, booking.service_id, booking.business_id, tenant_id)
        waitlist_customer = require_customer_in_business(
            db, entry.customer_id, entry.business_id, tenant_id
        )
        offer_intent = enqueue_waitlist_offer(
            db, entry=entry, business=business, customer=waitlist_customer, service=service,
        )
        waitlist_notification_ids.append(offer_intent.id)

    db.commit()
    db.refresh(booking)
    for notification_id in waitlist_notification_ids:
        enqueue_send_notification_job(notification_id)
    return booking


def expire_stale_payment_holds(db: Session) -> int:
    """Periodic maintenance (P3-008): expire PENDING_PAYMENT bookings whose
    hold has been outstanding longer than settings.booking_payment_hold_minutes
    (ADR 0004 SS4). Returns the number of holds actually expired.

    The candidate list below is a plain, unlocked snapshot -- by the time
    the loop reaches a given row, a payment webhook may have already
    confirmed it (or another maintenance tick already expired it).
    expire_pending_payment_hold() correctly raises ConflictError for that
    case once its own row lock sees the now-current status, but that is an
    expected, benign race here, not a real failure -- skip it and keep
    going rather than letting it propagate and abort the rest of this
    maintenance tick's unrelated cleanup (password reset tokens, audit
    logs, etc.), caught by cross-provider review as a follow-up to the
    confirm/expire locking fix above."""
    threshold = datetime.now(timezone.utc) - timedelta(
        minutes=settings.booking_payment_hold_minutes
    )
    stale = (
        db.query(Booking)
        .filter(
            Booking.status == BookingStatus.PENDING_PAYMENT,
            Booking.created_at < threshold,
        )
        .all()
    )
    expired_count = 0
    for booking in stale:
        try:
            expire_pending_payment_hold(db, booking.id, booking.business_id, booking.tenant_id)
            expired_count += 1
        except ConflictError:
            db.rollback()
    return expired_count


def refund_booking_payment(
    db: Session,
    booking_id: int,
    business_id: int,
    tenant_id: int,
    *,
    actor_id: int | None = None,
    reason: str | None = None,
) -> BookingPayment:
    """Manual admin-triggered refund recording (ADR 0004 SS6). Refund
    *policy* (full vs. partial, automatic vs. manual) is explicitly out of
    scope -- this only records that a refund happened (status=REFUNDED,
    refunded_at), the same way the ADR describes. Does not call any
    payment-provider API itself; the actual Stripe refund (P3-007) is
    assumed to have already been issued out-of-band by the admin performing
    this action. Does not require or change the linked Booking's status:
    the ADR does not mandate the booking be CANCELLED first, and a wrong
    default here would be inventing policy, not recording one."""
    booking = require_booking_in_business(db, booking_id, business_id, tenant_id)
    payment = (
        db.query(BookingPayment)
        .filter(BookingPayment.booking_id == booking.id, BookingPayment.tenant_id == tenant_id)
        .first()
    )
    if payment is None:
        raise NotFoundError("No payment found for this booking")
    if payment.status != BookingPaymentStatus.SUCCEEDED:
        raise ConflictError("Only a succeeded payment can be refunded")

    payment.status = BookingPaymentStatus.REFUNDED
    payment.refunded_at = datetime.now(timezone.utc)
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.BOOKING_PAYMENT_REFUNDED,
        target_booking_id=booking.id,
        source=reason,
        commit=False,
    )
    db.commit()
    db.refresh(payment)
    return payment


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


def _require_booking_in_business_for_update(
    db: Session, booking_id: int, business_id: int, tenant_id: int
) -> Booking:
    """Like require_booking_in_business(), but takes a row lock (blocking,
    not SKIP LOCKED -- there is exactly one row both sides of this race
    target, so the second caller should wait and then see the first
    caller's committed result, not silently skip it). Used by
    confirm_booking_payment(), expire_pending_payment_hold(), and
    cancel_booking(): a payment webhook confirming a hold, the maintenance
    sweep expiring the same hold, and an admin cancelling it directly can
    otherwise all read PENDING_PAYMENT concurrently and each "win," leaving
    the booking/payment rows inconsistent (e.g. a payment marked succeeded
    on a booking one of the other two just cancelled).
    Locking means whichever transaction commits first wins outright; the
    second re-reads the now-current status under the lock and correctly
    hits the existing status-mismatch ConflictError instead of corrupting
    state -- caught by cross-provider review, which flagged the unlocked
    version as exactly this race (the same class of bug AVS-TD-030/PR #45
    already had to fix for the waitlist-offer transition).

    populate_existing() matters here specifically because of
    expire_stale_payment_holds(): its own candidate query already loaded
    these same Booking rows into this session's identity map before
    calling this function per-row. Without populate_existing(), SQLAlchemy
    returns the already-identity-mapped Python object as-is and does NOT
    refresh its attributes from the row this query just (re-)fetched under
    the lock -- so a status flip committed by a concurrent transaction in
    the meantime would silently not be seen, defeating the lock-then-recheck
    this function exists for. Also caught by cross-provider review."""
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.tenant_id == tenant_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if booking is None:
        raise NotFoundError("Booking not found")
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
    override: bool = False,
) -> Booking:
    if override and not (reason or "").strip():
        raise BadRequestError("reason is required for an admin override cancellation")
    # Locked, not a plain SELECT: cancel_booking() can target a
    # PENDING_PAYMENT hold (an admin cancelling it directly), which races
    # against confirm_booking_payment()/expire_pending_payment_hold() the
    # same way those two race each other -- same fix, same reason, caught by
    # cross-provider review as a follow-up to that one.
    booking = _require_booking_in_business_for_update(db, booking_id, business_id, tenant_id)
    if booking.status == BookingStatus.CANCELLED:
        raise ConflictError("Booking is already cancelled")
    booking.status = BookingStatus.CANCELLED
    booking.cancel_reason = reason
    _fail_linked_pending_payment(db, booking)
    create_audit_log(
        db,
        tenant_id=tenant_id,
        admin_id=actor_id,
        action=AuditAction.BOOKING_OVERRIDE_CANCELLED if override else AuditAction.BOOKING_CANCELLED,
        target_booking_id=booking.id,
        source=reason if override else booking.source,
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
    reschedule rather than two unrelated events. Only a CONFIRMED booking
    can be rescheduled -- without this guard, rescheduling a PENDING_PAYMENT
    hold would cancel it (correctly) but then create_booking() the new slot
    straight to CONFIRMED, silently skipping payment entirely."""
    old_booking = require_booking_in_business(db, booking_id, business_id, tenant_id)
    if old_booking.status != BookingStatus.CONFIRMED:
        raise ConflictError("Only a confirmed booking can be rescheduled")
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
