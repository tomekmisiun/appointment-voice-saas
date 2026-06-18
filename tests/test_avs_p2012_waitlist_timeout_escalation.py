"""P2-012: expire stale waitlist offers and escalate to the next customer.

expire_stale_waitlist_offers() is the periodic maintenance counterpart to
P2-011's cancel_booking() trigger: an OFFERED entry whose offer has been
outstanding longer than settings.waitlist_offer_timeout_minutes is
expired, and the next eligible WAITING entry for the same business/
service/desired_date (and staff preference) is offered instead -- so a
non-responsive customer can't block the waitlist forever.
"""
from datetime import date, datetime, time, timedelta, timezone

from app.core.config import settings
from app.models.notification_outbox import NotificationOutbox, NotificationPurpose
from app.models.tenant import Tenant
from app.models.waitlist_entry import WaitlistEntry, WaitlistEntryStatus
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.waitlist_service import create_waitlist_entry, expire_stale_waitlist_offers


def _future_date(days: int = 7) -> date:
    return date.today() + timedelta(days=days)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Timeout Salon", timezone="UTC")
    svc = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    return tenant.id, biz, svc


def _make_offered_entry(
    db, tenant_id, biz, svc, *, phone, staff_id=None, offered_for_staff_id=None, stale: bool
):
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone=phone, name="Waiter"
    )
    entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, desired_date=_future_date(), staff_id=staff_id,
    )
    entry.status = WaitlistEntryStatus.OFFERED
    # Defaults to staff_id so existing callers (where the offered slot's
    # staff matches the customer's own preference) don't need to repeat it.
    entry.offered_for_staff_id = (
        offered_for_staff_id if offered_for_staff_id is not None else staff_id
    )
    db.commit()
    if stale:
        stale_time = (
            datetime.now(timezone.utc)
            - timedelta(minutes=settings.waitlist_offer_timeout_minutes + 5)
        )
        db.query(WaitlistEntry).filter(WaitlistEntry.id == entry.id).update(
            {"updated_at": stale_time}
        )
        db.commit()
    db.refresh(entry)
    return entry


def test_stale_offer_is_expired(db):
    tenant_id, biz, svc = _setup(db)
    entry = _make_offered_entry(db, tenant_id, biz, svc, phone="+48760000001", stale=True)

    count = expire_stale_waitlist_offers(db)

    db.refresh(entry)
    assert count == 1
    assert entry.status == WaitlistEntryStatus.EXPIRED


def test_recent_offer_is_not_expired(db):
    tenant_id, biz, svc = _setup(db)
    entry = _make_offered_entry(db, tenant_id, biz, svc, phone="+48760000002", stale=False)

    count = expire_stale_waitlist_offers(db)

    db.refresh(entry)
    assert count == 0
    assert entry.status == WaitlistEntryStatus.OFFERED


def test_expiry_escalates_to_next_waiting_entry(db):
    tenant_id, biz, svc = _setup(db)
    expired_entry = _make_offered_entry(db, tenant_id, biz, svc, phone="+48760000003", stale=True)

    next_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000004", name="Next In Line"
    )
    next_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=next_customer.id,
        service_id=svc.id, desired_date=expired_entry.desired_date,
    )

    expire_stale_waitlist_offers(db)

    db.refresh(next_entry)
    assert next_entry.status == WaitlistEntryStatus.OFFERED
    offer = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == "+48760000004",
        )
        .first()
    )
    assert offer is not None


def test_expiry_with_no_eligible_next_entry_does_not_error(db):
    tenant_id, biz, svc = _setup(db)
    entry = _make_offered_entry(db, tenant_id, biz, svc, phone="+48760000005", stale=True)

    count = expire_stale_waitlist_offers(db)

    db.refresh(entry)
    assert count == 1
    assert entry.status == WaitlistEntryStatus.EXPIRED


def test_escalation_respects_staff_preference(db):
    tenant_id, biz, svc = _setup(db)
    staff_a = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist A")
    staff_b = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist B")
    expired_entry = _make_offered_entry(
        db, tenant_id, biz, svc, phone="+48760000006", staff_id=staff_a.id, stale=True
    )

    wrong_staff_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000007", name="Wants B"
    )
    wants_b = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=wrong_staff_customer.id,
        service_id=svc.id, desired_date=expired_entry.desired_date, staff_id=staff_b.id,
    )
    any_staff_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000008", name="Any Staff"
    )
    wants_any = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=any_staff_customer.id,
        service_id=svc.id, desired_date=expired_entry.desired_date,
    )

    expire_stale_waitlist_offers(db)

    db.refresh(wants_b)
    db.refresh(wants_any)
    assert wants_b.status == WaitlistEntryStatus.WAITING
    assert wants_any.status == WaitlistEntryStatus.OFFERED


def test_escalation_after_cancellation_for_specific_staff_finds_staff_preferring_entry(db):
    """Regression: when the cancelled slot belonged to a specific staff
    member but the first (oldest, no-preference) waiter's offer expires,
    escalation must still match against the freed slot's actual staff
    (offered_for_staff_id), not the expired entry's own NULL preference --
    otherwise a customer who specifically wants that staff member is
    skipped even though their preference matches the freed slot."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    staff_a = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist A")
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booked_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000014", name="Booked"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=booked_customer.id,
        service_id=svc.id, staff_id=staff_a.id, starts_at=starts_at,
    )

    no_pref_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000015", name="No Preference"
    )
    no_pref_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=no_pref_customer.id,
        service_id=svc.id, desired_date=desired,
    )
    wants_a_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000016", name="Wants A"
    )
    wants_a_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=wants_a_customer.id,
        service_id=svc.id, desired_date=desired, staff_id=staff_a.id,
    )

    cancel_booking(db, booking.id, tenant_id, reason="customer_request")

    db.refresh(no_pref_entry)
    db.refresh(wants_a_entry)
    assert no_pref_entry.status == WaitlistEntryStatus.OFFERED
    assert no_pref_entry.offered_for_staff_id == staff_a.id
    assert wants_a_entry.status == WaitlistEntryStatus.WAITING

    stale_time = (
        datetime.now(timezone.utc)
        - timedelta(minutes=settings.waitlist_offer_timeout_minutes + 5)
    )
    db.query(WaitlistEntry).filter(WaitlistEntry.id == no_pref_entry.id).update(
        {"updated_at": stale_time}
    )
    db.commit()

    expire_stale_waitlist_offers(db)

    db.refresh(no_pref_entry)
    db.refresh(wants_a_entry)
    assert no_pref_entry.status == WaitlistEntryStatus.EXPIRED
    assert wants_a_entry.status == WaitlistEntryStatus.OFFERED


def test_cancellation_then_timeout_escalates_to_next_waiting_entry(db):
    """End-to-end P2-011 -> P2-012: a cancellation offers the slot to only
    the oldest matching waiter (P2-011); if that offer goes stale, P2-012
    expires it and offers the next-oldest waiter instead."""
    tenant_id, biz, svc = _setup(db)
    desired = _future_date()
    starts_at = datetime.combine(desired, time(10, 0), tzinfo=timezone.utc)
    booked_customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000011", name="Booked"
    )
    booking = create_booking(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=booked_customer.id,
        service_id=svc.id, staff_id=None, starts_at=starts_at,
    )

    first_waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000012", name="First Waiter"
    )
    second_waiter = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48760000013", name="Second Waiter"
    )
    first_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=first_waiter.id,
        service_id=svc.id, desired_date=desired,
    )
    second_entry = create_waitlist_entry(
        db, tenant_id=tenant_id, business_id=biz.id, customer_id=second_waiter.id,
        service_id=svc.id, desired_date=desired,
    )

    cancel_booking(db, booking.id, tenant_id, reason="customer_request")

    db.refresh(first_entry)
    db.refresh(second_entry)
    assert first_entry.status == WaitlistEntryStatus.OFFERED
    assert second_entry.status == WaitlistEntryStatus.WAITING

    stale_time = (
        datetime.now(timezone.utc)
        - timedelta(minutes=settings.waitlist_offer_timeout_minutes + 5)
    )
    db.query(WaitlistEntry).filter(WaitlistEntry.id == first_entry.id).update(
        {"updated_at": stale_time}
    )
    db.commit()

    expire_stale_waitlist_offers(db)

    db.refresh(first_entry)
    db.refresh(second_entry)
    assert first_entry.status == WaitlistEntryStatus.EXPIRED
    assert second_entry.status == WaitlistEntryStatus.OFFERED
    offer = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.tenant_id == tenant_id,
            NotificationOutbox.purpose == NotificationPurpose.WAITLIST_OFFER,
            NotificationOutbox.recipient_phone == "+48760000013",
        )
        .first()
    )
    assert offer is not None


def test_multiple_stale_offers_each_expired_independently(db):
    tenant_id, biz, svc = _setup(db)
    entry1 = _make_offered_entry(db, tenant_id, biz, svc, phone="+48760000009", stale=True)
    other_svc = create_service(
        db, tenant_id=tenant_id, business_id=biz.id, name="Color", duration_minutes=60
    )
    entry2 = _make_offered_entry(db, tenant_id, biz, other_svc, phone="+48760000010", stale=True)

    count = expire_stale_waitlist_offers(db)

    db.refresh(entry1)
    db.refresh(entry2)
    assert count == 2
    assert entry1.status == WaitlistEntryStatus.EXPIRED
    assert entry2.status == WaitlistEntryStatus.EXPIRED
