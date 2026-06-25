"""P3-008: pending-payment booking state (ADR 0004).

Covers the booking-lifecycle primitives ADR 0004 SS2-SS4 specify:
create_pending_payment_hold() (reserves the slot, no confirmation
side effects yet), confirm_booking_payment() (PENDING_PAYMENT -> CONFIRMED,
side effects fire here), expire_pending_payment_hold() (PENDING_PAYMENT ->
CANCELLED, no cancellation SMS, distinct audit action), and the
expire_stale_payment_holds() maintenance sweep. Does not cover any real
Stripe adapter/route -- that is P3-007, explicitly out of scope here.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.core.domain_errors import BadRequestError, ConflictError, NotFoundError
from app.models.audit_log import AuditAction
from app.models.booking import BookingStatus
from app.models.booking_payment import BookingPayment, BookingPaymentStatus
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.calendar_event import CalendarEvent
from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.models.user import User
from app.models.waitlist_entry import WaitlistEntry, WaitlistEntryStatus
from app.services.audit_log_service import get_audit_logs
from app.services.booking_service import (
    cancel_booking,
    confirm_booking_payment,
    create_booking,
    create_pending_payment_hold,
    expire_pending_payment_hold,
    expire_stale_payment_holds,
    refund_booking_payment,
    reschedule_booking,
)
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user

_STARTS_AT = datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc)


def _setup(db, *, deposit_required: bool = True):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Deposit Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Nina")
    svc = create_service(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        name="Color",
        duration_minutes=60,
        price_minor_units=10000,
        currency="PLN",
    )
    if deposit_required:
        svc.deposit_required = True
        svc.deposit_minor_units = 3000
        db.commit()
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48600300400"
    )
    return tenant.id, biz, staff, svc, customer


def _create_hold(db, *, tenant_id, biz, staff, svc, customer, starts_at=_STARTS_AT, **kwargs):
    return create_pending_payment_hold(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=starts_at,
        provider="stripe",
        **kwargs,
    )


# --- create_pending_payment_hold ---


def test_create_pending_payment_hold_reserves_slot_without_confirming(db):
    tenant_id, biz, staff, svc, customer = _setup(db)

    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    assert booking.status == BookingStatus.PENDING_PAYMENT
    payment = (
        db.query(BookingPayment).filter(BookingPayment.booking_id == booking.id).one()
    )
    assert payment.status == BookingPaymentStatus.PENDING
    assert payment.amount_minor_units == 3000
    assert payment.currency == "PLN"
    assert payment.provider == "stripe"

    # No confirmation SMS or calendar event yet -- those only fire on confirm.
    assert (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking.id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_CONFIRMATION,
        )
        .first()
        is None
    )
    assert db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).first() is None


def test_create_pending_payment_hold_rejects_service_without_deposit(db):
    tenant_id, biz, staff, svc, customer = _setup(db, deposit_required=False)

    with pytest.raises(BadRequestError):
        _create_hold(db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer)


def test_create_pending_payment_hold_blocked_by_existing_confirmed_booking(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )

    with pytest.raises(ConflictError):
        _create_hold(db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer)


def test_second_hold_for_same_slot_is_blocked_by_first_hold(db):
    """The exact race ADR 0004 SS3 exists to prevent: two customers both
    reaching checkout for the same staff/time slot."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    _create_hold(db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer)

    with pytest.raises(ConflictError):
        _create_hold(db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer)


# --- confirm_booking_payment ---


def test_confirm_booking_payment_transitions_to_confirmed_and_fires_side_effects(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    confirmed = confirm_booking_payment(
        db, booking.id, biz.id, tenant_id, provider_payment_id="pi_test_123"
    )

    assert confirmed.status == BookingStatus.CONFIRMED
    payment = (
        db.query(BookingPayment).filter(BookingPayment.booking_id == booking.id).one()
    )
    assert payment.status == BookingPaymentStatus.SUCCEEDED
    assert payment.provider_payment_id == "pi_test_123"
    assert payment.paid_at is not None

    confirmation = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking.id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_CONFIRMATION,
        )
        .first()
    )
    assert confirmation is not None
    assert db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).first() is not None

    logs = get_audit_logs(db, tenant_id)
    confirmed_logs = [
        log for log in logs
        if log.target_booking_id == booking.id and log.action == AuditAction.BOOKING_CONFIRMED
    ]
    assert len(confirmed_logs) == 1
    assert confirmed_logs[0].source == "stripe_webhook"


def test_confirm_booking_payment_rejects_non_pending_booking(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )

    with pytest.raises(ConflictError):
        confirm_booking_payment(db, booking.id, biz.id, tenant_id)


def test_confirm_booking_payment_rejects_already_succeeded_payment(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id)

    # Force the booking back to PENDING_PAYMENT to isolate the payment-status
    # check from the booking-status check above it.
    booking.status = BookingStatus.PENDING_PAYMENT
    db.commit()

    with pytest.raises(ConflictError):
        confirm_booking_payment(db, booking.id, biz.id, tenant_id)


def test_confirm_booking_payment_is_idempotent_for_duplicate_webhook_delivery(db):
    """Payment providers commonly redeliver/retry success events -- a
    second delivery for an already-confirmed payment must be a silent
    no-op, not a ConflictError or a duplicate confirmation SMS/calendar
    sync."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id, provider_payment_id="pi_test_456")

    again = confirm_booking_payment(
        db, booking.id, biz.id, tenant_id, provider_payment_id="pi_test_456"
    )

    assert again.status == BookingStatus.CONFIRMED
    confirmations = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking.id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_CONFIRMATION,
        )
        .all()
    )
    assert len(confirmations) == 1
    assert db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).count() == 1


# --- expire_pending_payment_hold ---


def test_expire_pending_payment_hold_cancels_without_cancellation_sms(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    expired = expire_pending_payment_hold(db, booking.id, biz.id, tenant_id)

    assert expired.status == BookingStatus.CANCELLED
    assert expired.cancel_reason == "payment_hold_expired"
    payment = (
        db.query(BookingPayment).filter(BookingPayment.booking_id == booking.id).one()
    )
    assert payment.status == BookingPaymentStatus.FAILED

    logs = get_audit_logs(db, tenant_id)
    actions = [log.action for log in logs if log.target_booking_id == booking.id]
    assert AuditAction.BOOKING_HOLD_EXPIRED in actions
    assert AuditAction.BOOKING_CANCELLED not in actions

    # No cancellation-style SMS -- the customer never had a confirmed booking.
    cancellation_sms = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking.id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_CANCELLATION,
        )
        .first()
    )
    assert cancellation_sms is None


def test_expire_pending_payment_hold_escalates_waitlist(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    waiting_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48600300401"
    )
    entry = WaitlistEntry(
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=waiting_customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        desired_date=_STARTS_AT.date(),
        status=WaitlistEntryStatus.WAITING,
    )
    db.add(entry)
    db.commit()

    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    expire_pending_payment_hold(db, booking.id, biz.id, tenant_id)

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.OFFERED
    offer = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER)
        .first()
    )
    assert offer is not None


def test_expire_pending_payment_hold_rejects_non_hold_booking(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )

    with pytest.raises(ConflictError):
        expire_pending_payment_hold(db, booking.id, biz.id, tenant_id)


# --- cancel_booking() admin path on a hold ---


def test_admin_cancel_of_pending_payment_hold_fails_linked_payment(db):
    """Distinct from auto-expiry: an admin deliberately cancelling a hold
    via the normal cancel endpoint still sends the regular cancellation SMS
    (this is a deliberate admin action, not a silent abandoned-checkout
    expiry) but must still mark the linked payment FAILED, not leave it
    PENDING forever."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    cancelled = cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer changed mind")

    assert cancelled.status == BookingStatus.CANCELLED
    payment = (
        db.query(BookingPayment).filter(BookingPayment.booking_id == booking.id).one()
    )
    assert payment.status == BookingPaymentStatus.FAILED
    assert payment.failure_reason == "customer changed mind"


# --- reschedule_booking() guard ---


def test_reschedule_rejects_pending_payment_booking(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    with pytest.raises(ConflictError):
        reschedule_booking(
            db,
            booking.id,
            biz.id,
            tenant_id,
            new_starts_at=_STARTS_AT + timedelta(hours=2),
        )


# --- expire_stale_payment_holds (maintenance sweep) ---


def test_expire_stale_payment_holds_expires_old_holds_only(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking_service.settings.booking_payment_hold_minutes", 15
    )
    tenant_id, biz, staff, svc, customer = _setup(db)
    stale_booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    stale_booking.created_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    db.commit()

    recent_booking = _create_hold(
        db,
        tenant_id=tenant_id,
        biz=biz,
        staff=staff,
        svc=svc,
        customer=customer,
        starts_at=_STARTS_AT + timedelta(hours=3),
    )

    count = expire_stale_payment_holds(db)

    assert count == 1
    db.refresh(stale_booking)
    db.refresh(recent_booking)
    assert stale_booking.status == BookingStatus.CANCELLED
    assert recent_booking.status == BookingStatus.PENDING_PAYMENT


def test_expire_stale_payment_holds_skips_a_concurrently_resolved_hold(db, monkeypatch):
    """A stale hold can be confirmed (or expired by another tick) between
    this sweep's candidate query and its turn in the loop -- that's an
    expected, benign race, not a real failure. The sweep must skip it (not
    count it, not propagate the ConflictError) and keep processing the rest
    of the batch, otherwise one race would abort the whole maintenance tick
    -- caught by cross-provider review as a follow-up to the confirm/expire
    locking fix."""
    monkeypatch.setattr(
        "app.services.booking_service.settings.booking_payment_hold_minutes", 15
    )
    tenant_id, biz, staff, svc, customer = _setup(db)
    stale_booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    stale_booking.created_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    db.commit()

    other_stale_booking = _create_hold(
        db,
        tenant_id=tenant_id,
        biz=biz,
        staff=staff,
        svc=svc,
        customer=customer,
        starts_at=_STARTS_AT + timedelta(hours=3),
    )
    other_stale_booking.created_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    db.commit()

    import app.services.booking_service as booking_service_module

    original_expire = booking_service_module.expire_pending_payment_hold

    def racy_expire(db, booking_id, business_id, tenant_id):
        if booking_id == stale_booking.id:
            # Simulate a payment webhook having confirmed this exact hold
            # in between the sweep's candidate query and this call.
            raise ConflictError("Booking is not a pending payment hold")
        return original_expire(db, booking_id, business_id, tenant_id)

    monkeypatch.setattr(booking_service_module, "expire_pending_payment_hold", racy_expire)

    count = expire_stale_payment_holds(db)

    assert count == 1
    db.refresh(other_stale_booking)
    assert other_stale_booking.status == BookingStatus.CANCELLED


# --- refund_booking_payment (ADR 0004 SS6: manual admin-triggered refund) ---


def test_refund_booking_payment_marks_payment_refunded(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id)

    payment = refund_booking_payment(
        db, booking.id, biz.id, tenant_id, reason="customer no-show goodwill refund"
    )

    assert payment.status == BookingPaymentStatus.REFUNDED
    assert payment.refunded_at is not None

    logs = get_audit_logs(db, tenant_id)
    entry = next(
        (
            log
            for log in logs
            if log.target_booking_id == booking.id
            and log.action == AuditAction.BOOKING_PAYMENT_REFUNDED
        ),
        None,
    )
    assert entry is not None
    assert entry.source == "customer no-show goodwill refund"


def test_refund_booking_payment_rejects_not_yet_succeeded_payment(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )

    with pytest.raises(ConflictError):
        refund_booking_payment(db, booking.id, biz.id, tenant_id)


def test_refund_booking_payment_rejects_double_refund(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id)
    refund_booking_payment(db, booking.id, biz.id, tenant_id)

    with pytest.raises(ConflictError):
        refund_booking_payment(db, booking.id, biz.id, tenant_id)


def test_refund_booking_payment_rejects_booking_without_payment(db):
    tenant_id, biz, staff, svc, customer = _setup(db, deposit_required=False)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )

    with pytest.raises(NotFoundError):
        refund_booking_payment(db, booking.id, biz.id, tenant_id)


# --- API layer: admin-only refund endpoint ---


def test_refund_booking_payment_api_endpoint(db, client):
    register_user(client, "refund_admin@example.com")
    promote_to_admin(db, "refund_admin@example.com")
    token = login_user(client, "refund_admin@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    user = db.query(User).filter(User.email == "refund_admin@example.com").one()
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz.id,
        user_id=user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id)

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/refund",
        json={"reason": "support escalation"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "refunded"


def test_refund_booking_payment_api_requires_admin(db, client):
    register_user(client, "refund_member@example.com")
    token = login_user(client, "refund_member@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = _create_hold(
        db, tenant_id=tenant_id, biz=biz, staff=staff, svc=svc, customer=customer
    )
    confirm_booking_payment(db, booking.id, biz.id, tenant_id)

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/refund",
        json={"reason": "support escalation"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403
