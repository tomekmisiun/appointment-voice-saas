"""Regression test for the payment-hold confirm/expire race (P3-008, ADR
0004 SS4/SS5).

Before this fix, confirm_booking_payment() and expire_pending_payment_hold()
both read Booking.status with a bare SELECT and then wrote it, with no
locking. A payment webhook confirming a hold and the maintenance sweep
expiring that same hold could run concurrently and both "win," leaving the
booking and its BookingPayment in an inconsistent combination (e.g. a
payment marked succeeded on a booking the other transaction just cancelled).
The fix takes a row lock (with_for_update(), blocking) on the booking before
either transition. This test uses real threads with separate DB sessions
(not just sequential calls) so the underlying Postgres row lock is actually
exercised -- caught by cross-provider review, the same class of bug
AVS-TD-030/PR #45 already had to fix for the waitlist-offer transition."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from app.core.domain_errors import ConflictError
from app.models.booking import BookingStatus
from app.models.booking_payment import BookingPayment, BookingPaymentStatus
from app.models.tenant import Tenant
import app.services.booking_service as booking_service
from app.services.booking_service import create_pending_payment_hold
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import TestingSessionLocal

_STARTS_AT = datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Concurrency Deposit Salon", timezone="UTC")
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
    svc.deposit_required = True
    svc.deposit_minor_units = 3000
    db.commit()
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48600300500"
    )
    return tenant.id, biz, staff, svc, customer


def test_concurrent_confirm_and_expire_resolve_to_exactly_one_outcome(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_pending_payment_hold(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
        provider="stripe",
    )
    booking_id = booking.id

    results: dict[str, str] = {}

    def confirm() -> None:
        session = TestingSessionLocal()
        try:
            booking_service.confirm_booking_payment(session, booking_id, biz.id, tenant_id)
            results["confirm"] = "ok"
        except ConflictError:
            results["confirm"] = "conflict"
        finally:
            session.close()

    def expire() -> None:
        session = TestingSessionLocal()
        try:
            booking_service.expire_pending_payment_hold(session, booking_id, biz.id, tenant_id)
            results["expire"] = "ok"
        except ConflictError:
            results["expire"] = "conflict"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda fn: fn(), [confirm, expire]))

    # Exactly one side won outright; the other's locked re-read of the
    # now-current status correctly raised ConflictError instead of also
    # applying its own transition on top.
    assert sorted(results.values()) == ["conflict", "ok"]

    db.expire_all()
    booking = booking_service.require_booking_in_business(db, booking_id, biz.id, tenant_id)
    payment = db.query(BookingPayment).filter(BookingPayment.booking_id == booking_id).one()

    if results["confirm"] == "ok":
        assert booking.status == BookingStatus.CONFIRMED
        assert payment.status == BookingPaymentStatus.SUCCEEDED
    else:
        assert booking.status == BookingStatus.CANCELLED
        assert payment.status == BookingPaymentStatus.FAILED


def test_concurrent_expires_of_the_same_hold_only_one_succeeds(db):
    """Two overlapping maintenance ticks racing to expire the same stale
    hold -- the second must see CANCELLED already and conflict, not
    double-expire or double-escalate the waitlist."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_pending_payment_hold(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
        provider="stripe",
    )
    booking_id = booking.id

    results: dict[int, str] = {}

    def expire(worker_id: int) -> None:
        session = TestingSessionLocal()
        try:
            booking_service.expire_pending_payment_hold(session, booking_id, biz.id, tenant_id)
            results[worker_id] = "ok"
        except ConflictError:
            results[worker_id] = "conflict"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(expire, [1, 2]))

    assert sorted(results.values()) == ["conflict", "ok"]


def test_locked_refetch_sees_a_concurrent_confirm_even_when_already_in_identity_map(db):
    """Direct regression for the identity-map gap cross-provider review
    caught: expire_stale_payment_holds()'s own candidate query loads a
    Booking into this session's identity map *before*
    expire_pending_payment_hold() takes the row lock on it. Without
    populate_existing() on that locked re-fetch, SQLAlchemy would return the
    already-mapped (stale) Python object as-is instead of refreshing it from
    the row the lock just (re-)read -- silently defeating the
    lock-then-recheck this function exists for. Reproduces that exact
    ordering directly, without needing a real maintenance-tick sweep."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_pending_payment_hold(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
        provider="stripe",
    )
    booking_id = booking.id

    # Load it into THIS session's identity map first, exactly as
    # expire_stale_payment_holds()'s own candidate query would.
    preloaded = (
        db.query(booking_service.Booking)
        .filter(booking_service.Booking.id == booking_id)
        .one()
    )
    assert preloaded.status == BookingStatus.PENDING_PAYMENT

    # A concurrent payment webhook confirms it via a separate session/commit.
    other_session = TestingSessionLocal()
    try:
        booking_service.confirm_booking_payment(other_session, booking_id, biz.id, tenant_id)
    finally:
        other_session.close()

    # expire_pending_payment_hold() runs in the SAME session that still has
    # the stale PENDING_PAYMENT object cached -- it must see CONFIRMED now
    # (via populate_existing()) and raise, not cancel an already-paid booking.
    with pytest.raises(ConflictError):
        booking_service.expire_pending_payment_hold(db, booking_id, biz.id, tenant_id)

    db.expire_all()
    refreshed = booking_service.require_booking_in_business(db, booking_id, biz.id, tenant_id)
    assert refreshed.status == BookingStatus.CONFIRMED
