"""Tests for booking notification enqueueing (AVS-E004, AVS-E005)."""

from datetime import datetime, timezone

from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.tenant import Tenant
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff


_STARTS_AT = datetime(2027, 9, 1, 9, 0, 0, tzinfo=timezone.utc)


def _setup(db, *, business_phone: str | None = "+48600000000"):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(
        db,
        tenant_id=tenant.id,
        name="Notify Salon",
        timezone="Europe/Warsaw",
        phone=business_phone,
    )
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48600100200"
    )
    return tenant.id, biz, staff.id, svc, customer


def _outbox_for_booking(db, booking_id):
    return (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.booking_id == booking_id)
        .order_by(NotificationOutbox.id.asc())
        .all()
    )


def test_create_booking_enqueues_customer_and_business_confirmation(db):
    tenant_id, biz, staff_id, svc, customer = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    intents = _outbox_for_booking(db, booking.id)
    assert len(intents) == 2

    customer_intent = next(i for i in intents if i.recipient_phone == customer.phone)
    business_intent = next(i for i in intents if i.recipient_phone == biz.phone)

    for intent in (customer_intent, business_intent):
        assert intent.tenant_id == tenant_id
        assert intent.business_id == biz.id
        assert intent.channel == NotificationChannel.SMS
        assert intent.purpose == NotificationPurpose.BOOKING_CONFIRMATION
        assert intent.status == NotificationStatus.PENDING
        assert intent.body


def test_create_booking_skips_business_intent_without_business_phone(db):
    tenant_id, biz, staff_id, svc, customer = _setup(db, business_phone=None)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    intents = _outbox_for_booking(db, booking.id)
    assert len(intents) == 1
    assert intents[0].recipient_phone == customer.phone


def test_booking_confirmation_intents_isolated_to_tenant(db):
    tenant_id, biz, staff_id, svc, customer = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    other_tenant_intents = (
        db.query(NotificationOutbox)
        .filter(NotificationOutbox.tenant_id == 99999, NotificationOutbox.booking_id == booking.id)
        .all()
    )
    assert other_tenant_intents == []


def test_cancel_booking_enqueues_customer_and_business_cancellation(db):
    tenant_id, biz, staff_id, svc, customer = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    cancel_booking(db, booking.id, tenant_id, reason="Client request")

    intents = _outbox_for_booking(db, booking.id)
    cancellation_intents = [
        i for i in intents if i.purpose == NotificationPurpose.BOOKING_CANCELLATION
    ]
    assert len(cancellation_intents) == 2

    customer_intent = next(i for i in cancellation_intents if i.recipient_phone == customer.phone)
    business_intent = next(i for i in cancellation_intents if i.recipient_phone == biz.phone)

    for intent in (customer_intent, business_intent):
        assert intent.tenant_id == tenant_id
        assert intent.business_id == biz.id
        assert intent.channel == NotificationChannel.SMS
        assert intent.status == NotificationStatus.PENDING
        assert intent.body


def test_cancel_booking_skips_business_intent_without_business_phone(db):
    tenant_id, biz, staff_id, svc, customer = _setup(db, business_phone=None)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    cancel_booking(db, booking.id, tenant_id, reason="Client request")

    intents = _outbox_for_booking(db, booking.id)
    cancellation_intents = [
        i for i in intents if i.purpose == NotificationPurpose.BOOKING_CANCELLATION
    ]
    assert len(cancellation_intents) == 1
    assert cancellation_intents[0].recipient_phone == customer.phone
