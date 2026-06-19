"""P2-011: offer the waitlist after a cancellation.

cancel_booking() now looks up WAITING WaitlistEntry rows matching the
cancelled booking's business/service/date (and staff, if the entry asked
for a specific one), transitions the oldest match to OFFERED, and enqueues
a WAITLIST_OFFER SMS notification. Only the oldest match is offered -- the
rest stay WAITING; if the offered customer doesn't respond in time,
P2-012's expire_stale_waitlist_offers() escalates to the next one.
"""
from datetime import date, datetime, time, timedelta, timezone

from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.models.waitlist_entry import WaitlistEntryStatus
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.waitlist_service import create_waitlist_entry, update_waitlist_entry_status


def _future_date(days: int = 7) -> date:
    return date.today() + timedelta(days=days)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Waitlist Offer Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    return tenant.id, biz, svc


def _book(db, tenant_id, biz, svc, *, phone, starts_at, staff_id=None):
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone=phone, name="Booked Customer"
    )
    return create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, staff_id=staff_id, starts_at=starts_at,
    )


def test_cancellation_offers_waiting_entry_for_same_service_and_date(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000001", starts_at=starts_at)

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000002", name="Waiting Customer"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.OFFERED
    offer = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == "+48750000002",
        )
        .first()
    )
    assert offer is not None
    assert "haircut" in offer.body.lower()


def test_entry_for_different_date_is_not_offered(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    other_date = _future_date(8)
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000003", starts_at=starts_at)

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000004", name="Wrong Date"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=other_date,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.WAITING


def test_entry_for_different_service_is_not_offered(db):
    tenant_id, biz, svc = _setup(db)
    other_svc = create_service(
        db, tenant_id=tenant_id, business_id=biz.id, name="Color", duration_minutes=60
    )
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000005", starts_at=starts_at)

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000006", name="Wrong Service"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=other_svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.WAITING


def test_entry_wanting_specific_staff_only_offered_when_that_staff_freed_up(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    staff_a = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist A")
    staff_b = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist B")
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(
        db, tenant_id, biz, svc, phone="+48750000007", starts_at=starts_at, staff_id=staff_a.id
    )

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000008", name="Wants B"
    )
    entry_wants_b = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired, staff_id=staff_b.id,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry_wants_b)
    assert entry_wants_b.status == WaitlistEntryStatus.WAITING


def test_entry_with_no_staff_preference_is_offered_regardless_of_cancelled_staff(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    staff_a = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist A")
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(
        db, tenant_id, biz, svc, phone="+48750000009", starts_at=starts_at, staff_id=staff_a.id
    )

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000010", name="No Preference"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.OFFERED


def test_multiple_eligible_entries_only_oldest_is_offered(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000011", starts_at=starts_at)

    waiter1 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000012", name="First Waiter"
    )
    waiter2 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000013", name="Second Waiter"
    )
    entry1 = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter1.id,
        service_id=svc.id, desired_date=desired,
    )
    entry2 = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter2.id,
        service_id=svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry1)
    db.refresh(entry2)
    assert entry1.status == WaitlistEntryStatus.OFFERED
    assert entry2.status == WaitlistEntryStatus.WAITING


def test_already_offered_entry_is_not_re_offered(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000014", starts_at=starts_at)

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48750000015", name="Already Offered"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired,
    )
    update_waitlist_entry_status(db, entry.id, tenant_id, status=WaitlistEntryStatus.OFFERED)

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    offers = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == "+48750000015",
        )
        .all()
    )
    assert offers == []


def test_cancellation_with_no_matching_waitlist_entries_does_not_error(db):
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000016", starts_at=starts_at)

    cancelled = cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    assert cancelled.status == "cancelled"


def test_waitlist_entry_from_another_business_is_not_offered(db):
    tenant_id, biz, svc = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_svc = create_service(
        db, tenant_id=tenant.id, business_id=other_biz.id, name="Haircut", duration_minutes=30
    )
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booking = _book(db, tenant_id, biz, svc, phone="+48750000017", starts_at=starts_at)

    other_waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=other_biz.id, phone="+48750000018", name="Other Biz Waiter"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=other_biz.id, customer_id=other_waiter.id,
        service_id=other_svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.WAITING
