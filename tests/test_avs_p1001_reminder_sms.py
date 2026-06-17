"""P1-001: reminder SMS.

`enqueue_due_reminders()` queues a BOOKING_REMINDER notification for confirmed
bookings starting within `settings.reminder_lead_minutes`, exactly once per
booking, and enqueues the SEND_NOTIFICATION_JOB worker job.

Assertions are scoped to each test's own booking via `_reminder_rows()`
rather than the function's global return count, because the shared test
database is not transactionally isolated across tests (services commit
eagerly) and other suites create bookings near "now" too.
"""
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.notification_service import enqueue_due_reminders
from app.services.service_service import create_service


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reminder Salon", timezone="UTC")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48700000000"
    )
    return tenant.id, biz, svc, customer


def _reminder_rows(db, booking_id):
    return (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.booking_id == booking_id,
            NotificationOutbox.purpose == NotificationPurpose.BOOKING_REMINDER,
        )
        .all()
    )


def _book_at(db, tenant_id, biz, svc, customer, starts_at):
    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=starts_at,
    )


def test_booking_due_within_lead_window_gets_reminder(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.reminder_lead_minutes - 10
    )
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)

    enqueue_due_reminders(db)

    rows = _reminder_rows(db, booking.id)
    assert len(rows) == 1
    assert rows[0].recipient_phone == customer.phone
    assert svc.name in rows[0].body


def test_booking_outside_lead_window_is_not_reminded(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.reminder_lead_minutes + 60
    )
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []


def test_past_booking_is_not_reminded(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []


def test_cancelled_booking_is_not_reminded(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    cancel_booking(db, booking.id, tenant_id)

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []


def test_reminder_is_sent_only_once(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)

    enqueue_due_reminders(db)
    enqueue_due_reminders(db)

    assert len(_reminder_rows(db, booking.id)) == 1


def test_enqueue_due_reminders_covers_multiple_bookings(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    first = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    second = _book_at(db, tenant_id, biz, svc, customer, starts_at + timedelta(minutes=5))

    enqueue_due_reminders(db)

    assert len(_reminder_rows(db, first.id)) == 1
    assert len(_reminder_rows(db, second.id)) == 1
