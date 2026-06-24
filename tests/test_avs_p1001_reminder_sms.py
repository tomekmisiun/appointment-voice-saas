"""P1-001: reminder SMS.

`enqueue_due_reminders()` queues a BOOKING_REMINDER notification for confirmed
bookings starting within `settings.reminder_lead_minutes`, exactly once per
booking, and enqueues the SEND_NOTIFICATION_JOB worker job. It also skips
bookings made with less than `settings.reminder_min_advance_minutes` of
notice (e.g. booked today for tomorrow) -- those are already within the
lead window the moment they're created, so a reminder would land right next
to the confirmation SMS for no reason.

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


def _backdate_creation(db, booking, *, advance_minutes):
    """Simulate a booking made `advance_minutes` before its own starts_at,
    rather than "just now" (the default from create_booking()) -- needed to
    exercise the reminder-lead-window logic independently of the new
    minimum-advance-notice guard below, which the real create_booking() call
    in these tests would otherwise always fail (starts_at is set only
    minutes after "now" in most of these tests)."""
    booking.created_at = booking.starts_at - timedelta(minutes=advance_minutes)
    db.commit()


def test_booking_due_within_lead_window_gets_reminder(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.reminder_lead_minutes - 10
    )
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    _backdate_creation(db, booking, advance_minutes=settings.reminder_min_advance_minutes + 60)

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
    _backdate_creation(db, booking, advance_minutes=settings.reminder_min_advance_minutes + 60)
    cancel_booking(db, booking.id, biz.id, tenant_id)

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []


def test_reminder_is_sent_only_once(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    _backdate_creation(db, booking, advance_minutes=settings.reminder_min_advance_minutes + 60)

    enqueue_due_reminders(db)
    enqueue_due_reminders(db)

    assert len(_reminder_rows(db, booking.id)) == 1


def test_enqueue_due_reminders_covers_multiple_bookings(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    first = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    second = _book_at(db, tenant_id, biz, svc, customer, starts_at + timedelta(minutes=5))
    _backdate_creation(db, first, advance_minutes=settings.reminder_min_advance_minutes + 60)
    _backdate_creation(db, second, advance_minutes=settings.reminder_min_advance_minutes + 60)

    enqueue_due_reminders(db)

    assert len(_reminder_rows(db, first.id)) == 1
    assert len(_reminder_rows(db, second.id)) == 1


# Minimum advance notice (last-minute bookings shouldn't get a redundant
# reminder right after their confirmation SMS)


def test_booking_made_last_minute_is_not_reminded(db):
    """The exact case this guard exists for: booking today for a slot
    that's already within the reminder lead window (e.g. "today for
    tomorrow") must not also get a reminder seconds/minutes after the
    confirmation SMS."""
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    # created_at is "now" (the default from create_booking()) -- only ~30
    # minutes of advance notice, far under reminder_min_advance_minutes.

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []


def test_booking_with_exactly_minimum_advance_notice_gets_reminder(db):
    """Boundary: advance notice exactly equal to the threshold is enough
    (the guard blocks strictly-less-than, not less-than-or-equal)."""
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    _backdate_creation(db, booking, advance_minutes=settings.reminder_min_advance_minutes)

    enqueue_due_reminders(db)

    assert len(_reminder_rows(db, booking.id)) == 1


def test_booking_just_under_minimum_advance_notice_is_not_reminded(db):
    tenant_id, biz, svc, customer = _setup(db)
    starts_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    booking = _book_at(db, tenant_id, biz, svc, customer, starts_at)
    _backdate_creation(db, booking, advance_minutes=settings.reminder_min_advance_minutes - 1)

    enqueue_due_reminders(db)

    assert _reminder_rows(db, booking.id) == []
