"""P1-002: SMS reply confirm/cancel.

`handle_sms_reply()` parses a simple "C"/"CONFIRM" or "X"/"CANCEL" text reply
and acts on the customer's soonest upcoming confirmed booking. CANCEL is
idempotent (re-sending after cancellation is a no-op, not an error). CONFIRM
is also a no-op since bookings are already confirmed at creation.
"""
from datetime import datetime, timedelta, timezone

from app.models.booking import BookingStatus
from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.sms_reply_service import SmsReplyIntent, handle_sms_reply, parse_reply_intent


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reply Salon", timezone="UTC")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48800000000"
    )
    return tenant.id, biz, svc, customer


def _book(db, tenant_id, biz, svc, customer, starts_at=None):
    starts_at = starts_at or datetime.now(timezone.utc) + timedelta(hours=2)
    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=starts_at,
    )


def test_parse_reply_intent_recognizes_confirm_variants():
    for text in ["c", "C", " confirm ", "Confirm", "y", "YES"]:
        assert parse_reply_intent(text) == SmsReplyIntent.CONFIRM


def test_parse_reply_intent_recognizes_cancel_variants():
    for text in ["x", "X", " cancel ", "Cancel", "n", "NO"]:
        assert parse_reply_intent(text) == SmsReplyIntent.CANCEL


def test_parse_reply_intent_unrecognized_for_free_text():
    assert parse_reply_intent("what time is my appointment?") == SmsReplyIntent.UNRECOGNIZED


def test_cancel_reply_cancels_soonest_upcoming_booking(db):
    tenant_id, biz, svc, customer = _setup(db)
    booking = _book(db, tenant_id, biz, svc, customer)

    intent = handle_sms_reply(
        db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="X"
    )

    assert intent == SmsReplyIntent.CANCEL
    db.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancel_reason == "customer_sms_reply"


def test_cancel_reply_is_idempotent(db):
    tenant_id, biz, svc, customer = _setup(db)
    booking = _book(db, tenant_id, biz, svc, customer)

    handle_sms_reply(db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="X")
    second_intent = handle_sms_reply(
        db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="cancel"
    )

    assert second_intent == SmsReplyIntent.CANCEL
    db.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


def test_confirm_reply_does_not_change_booking_state(db):
    tenant_id, biz, svc, customer = _setup(db)
    booking = _book(db, tenant_id, biz, svc, customer)

    intent = handle_sms_reply(
        db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="C"
    )

    assert intent == SmsReplyIntent.CONFIRM
    db.refresh(booking)
    assert booking.status == BookingStatus.CONFIRMED


def test_unrecognized_reply_does_not_touch_booking(db):
    tenant_id, biz, svc, customer = _setup(db)
    booking = _book(db, tenant_id, biz, svc, customer)

    intent = handle_sms_reply(
        db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="huh?"
    )

    assert intent == SmsReplyIntent.UNRECOGNIZED
    db.refresh(booking)
    assert booking.status == BookingStatus.CONFIRMED


def test_reply_from_unknown_phone_is_noop(db):
    tenant_id, biz, svc, customer = _setup(db)
    _book(db, tenant_id, biz, svc, customer)

    intent = handle_sms_reply(
        db, business_id=biz.id, tenant_id=tenant_id, from_phone="+48899999999", body="X"
    )

    assert intent == SmsReplyIntent.CANCEL


def test_cancel_reply_ignores_past_booking(db):
    tenant_id, biz, svc, customer = _setup(db)
    past_booking = _book(
        db, tenant_id, biz, svc, customer, starts_at=datetime.now(timezone.utc) - timedelta(hours=2)
    )

    handle_sms_reply(db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="X")

    db.refresh(past_booking)
    assert past_booking.status == BookingStatus.CONFIRMED


def test_cancel_reply_targets_soonest_of_multiple_bookings(db):
    tenant_id, biz, svc, customer = _setup(db)
    soonest = _book(db, tenant_id, biz, svc, customer, starts_at=datetime.now(timezone.utc) + timedelta(hours=1))
    later = _book(db, tenant_id, biz, svc, customer, starts_at=datetime.now(timezone.utc) + timedelta(days=1))

    handle_sms_reply(db, business_id=biz.id, tenant_id=tenant_id, from_phone=customer.phone, body="X")

    db.refresh(soonest)
    db.refresh(later)
    assert soonest.status == BookingStatus.CANCELLED
    assert later.status == BookingStatus.CONFIRMED
