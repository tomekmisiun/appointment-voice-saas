"""Regression tests for the waitlist offer race condition (AVS-TD-030).

Before this fix, find_matching_waitlist_entries() was a bare SELECT with no
row-level locking. Two concurrent cancellations (or a cancellation racing a
maintenance-tick escalation) matching the same WAITING entry could both read
it before either committed, and both flip it to OFFERED -- sending the same
customer two offers for slots that no longer both exist. The fix adds
SELECT ... FOR UPDATE SKIP LOCKED around the match-then-offer transition in
both cancel_booking() and the P2-012 escalation path.

These tests use real threads with separate DB sessions (not just sequential
calls) so the underlying Postgres row lock is actually exercised -- a
sequential test would pass even without the fix, since by the time the
second call runs, the first has already committed and the entry is no
longer WAITING.
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta, timezone

from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.models.waitlist_entry import WaitlistEntry, WaitlistEntryStatus
import app.services.booking_service as booking_service
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
import app.services.waitlist_service as waitlist_service
from app.services.waitlist_service import (
    create_waitlist_entry,
    expire_stale_waitlist_offers,
    find_matching_waitlist_entries,
)
from tests.database import TestingSessionLocal


def _future_date(days: int = 7) -> date:
    return date.today() + timedelta(days=days)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Concurrency Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    return tenant.id, biz, svc


def test_for_update_skip_locked_prevents_double_match(db):
    """Direct proof of the locking primitive: while one transaction holds
    the row lock on the only matching entry (acquired but not yet
    committed), a concurrent transaction's locked lookup must not see it."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000001", name="Waiter"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    session_a = TestingSessionLocal()
    session_b = TestingSessionLocal()
    try:
        locked_by_a = find_matching_waitlist_entries(
            session_a,
            business_id=biz.id,
            tenant_id=tenant_id,
            service_id=svc.id,
            desired_date=desired,
            staff_id=None,
            for_update=True,
        )
        assert [e.id for e in locked_by_a] == [entry.id]

        # B's locked lookup must skip the row A is holding -- not block, not see it.
        seen_by_b = find_matching_waitlist_entries(
            session_b,
            business_id=biz.id,
            tenant_id=tenant_id,
            service_id=svc.id,
            desired_date=desired,
            staff_id=None,
            for_update=True,
        )
        assert seen_by_b == []

        session_a.commit()

        # After A's transaction ends (lock released), B still sees nothing
        # new to match because A never changed the row in this test -- but
        # once A flips it to OFFERED and commits, the WAITING filter alone
        # (even without locking) excludes it for any later caller.
        entry_row = locked_by_a[0]
        entry_row.status = WaitlistEntryStatus.OFFERED
        session_a.commit()

        seen_by_b_after_commit = find_matching_waitlist_entries(
            session_b,
            business_id=biz.id,
            tenant_id=tenant_id,
            service_id=svc.id,
            desired_date=desired,
            staff_id=None,
            for_update=True,
        )
        assert seen_by_b_after_commit == []
    finally:
        session_a.close()
        session_b.close()


def test_concurrent_cancellations_offer_waitlist_entry_exactly_once(db, monkeypatch):
    """End-to-end: two bookings for the same business/service/date, both
    eligible to satisfy the single WAITING entry, cancelled concurrently
    from separate threads/sessions. Exactly one offer must result."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at_1 = datetime.combine(desired, time(9, 0), tzinfo=timezone.utc)
    starts_at_2 = datetime.combine(desired, time(14, 0), tzinfo=timezone.utc)

    customer_1 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000002", name="Booked 1"
    )
    customer_2 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000003", name="Booked 2"
    )
    booking_1 = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer_1.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at_1,
    )
    booking_2 = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer_2.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at_2,
    )

    waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000004", name="Waiter"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    # Force both threads' locked SELECTs to happen before either is allowed
    # to proceed to mutate+commit, so the race is actually exercised instead
    # of one cancellation finishing before the other even starts.
    barrier = threading.Barrier(2, timeout=5)
    original_find = booking_service.find_matching_waitlist_entries

    def synced_find(*args, **kwargs):
        result = original_find(*args, **kwargs)
        barrier.wait()
        return result

    monkeypatch.setattr(booking_service, "find_matching_waitlist_entries", synced_find)

    def cancel(booking_id: int) -> None:
        session = TestingSessionLocal()
        try:
            booking_service.cancel_booking(
                session, booking_id, biz.id, tenant_id, reason="concurrency_test"
            )
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(cancel, [booking_1.id, booking_2.id]))

    db.refresh(entry)
    assert entry.status == WaitlistEntryStatus.OFFERED

    offers = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == waiter.phone,
        )
        .all()
    )
    assert len(offers) == 1


def test_concurrent_cancellations_each_offer_a_different_waiter(db, monkeypatch):
    """Two freed slots, two eligible WAITING entries: locking must not
    over-claim. If the lock scoped to the whole matching list (not just the
    one row each caller actually offers), the first transaction would lock
    both candidate entries while only using one, and the second concurrent
    cancellation would see "no one waiting" via SKIP LOCKED even though a
    different waiter was genuinely free -- losing a real offer."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at_1 = datetime.combine(desired, time(9, 0), tzinfo=timezone.utc)
    starts_at_2 = datetime.combine(desired, time(14, 0), tzinfo=timezone.utc)

    customer_1 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000008", name="Booked 1"
    )
    customer_2 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000009", name="Booked 2"
    )
    booking_1 = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer_1.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at_1,
    )
    booking_2 = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer_2.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at_2,
    )

    waiter_1 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000010", name="Waiter 1"
    )
    waiter_2 = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000011", name="Waiter 2"
    )
    entry_1 = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter_1.id,
        service_id=svc.id, desired_date=desired,
    )
    entry_2 = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=waiter_2.id,
        service_id=svc.id, desired_date=desired,
    )

    barrier = threading.Barrier(2, timeout=5)
    original_find = booking_service.find_matching_waitlist_entries

    def synced_find(*args, **kwargs):
        result = original_find(*args, **kwargs)
        barrier.wait()
        return result

    monkeypatch.setattr(booking_service, "find_matching_waitlist_entries", synced_find)

    def cancel(booking_id: int) -> None:
        session = TestingSessionLocal()
        try:
            booking_service.cancel_booking(
                session, booking_id, biz.id, tenant_id, reason="concurrency_test"
            )
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(cancel, [booking_1.id, booking_2.id]))

    db.refresh(entry_1)
    db.refresh(entry_2)
    assert entry_1.status == WaitlistEntryStatus.OFFERED
    assert entry_2.status == WaitlistEntryStatus.OFFERED

    offers = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.business_id == biz.id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
        )
        .all()
    )
    offered_phones = {o.recipient_phone for o in offers}
    assert offered_phones == {waiter_1.phone, waiter_2.phone}


def test_concurrent_maintenance_ticks_do_not_double_escalate(db, monkeypatch):
    """Two overlapping calls to expire_stale_waitlist_offers() (simulating
    overlapping/retried maintenance ticks) must escalate a given stale
    offer at most once, not twice."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)

    booked_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000005", name="Booked"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=booked_customer.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at,
    )

    first_waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000006", name="First Waiter"
    )
    second_waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48790000007", name="Second Waiter"
    )
    first_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=first_waiter.id,
        service_id=svc.id, desired_date=desired,
    )
    second_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=second_waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    booking_service.cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer_request")

    db.refresh(first_entry)
    assert first_entry.status == WaitlistEntryStatus.OFFERED

    from app.core.config import settings

    stale_time = (
        datetime.now(timezone.utc)
        - timedelta(minutes=settings.waitlist_offer_timeout_minutes + 5)
    )
    db.query(WaitlistEntry).filter(WaitlistEntry.id == first_entry.id).update(
        {"updated_at": stale_time}
    )
    db.commit()

    # Force both threads' locked SELECTs to happen before either is allowed
    # to proceed to expire/escalate/commit, so the race is actually
    # exercised: both reach the barrier regardless of whether their own
    # query won the lock (got the row) or lost it (skipped, empty list).
    barrier = threading.Barrier(2, timeout=5)
    original_lock = waitlist_service._lock_stale_offered_entries

    def synced_lock(*args, **kwargs):
        result = original_lock(*args, **kwargs)
        barrier.wait()
        return result

    monkeypatch.setattr(waitlist_service, "_lock_stale_offered_entries", synced_lock)

    def expire_once() -> int:
        session = TestingSessionLocal()
        try:
            return expire_stale_waitlist_offers(session)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: expire_once(), range(2)))

    # SKIP LOCKED means exactly one tick processes the row; the other finds
    # it already locked and reports zero stale entries for this run.
    assert sorted(results) == [0, 1]

    db.refresh(first_entry)
    db.refresh(second_entry)
    assert first_entry.status == WaitlistEntryStatus.EXPIRED
    assert second_entry.status == WaitlistEntryStatus.OFFERED

    offers = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == second_waiter.phone,
        )
        .all()
    )
    assert len(offers) == 1
