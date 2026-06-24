"""Tests for Availability engine (AVS-C001–AVS-C006)."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.models.tenant import Tenant
from app.services.availability_service import get_available_slots
from app.services.availability_exception_service import create_availability_exception
from app.services.booking_service import create_booking, cancel_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service, require_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours
from tests.database import auth_headers, login_user, promote_to_admin, register_user


FUTURE_DATE = date(2027, 7, 7)  # Wednesday (weekday 2); UTC+2 in Warsaw (CEST)


@pytest.fixture()
def domain(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    business = create_business(
        db, tenant_id=tenant.id, name="Test Salon", timezone="Europe/Warsaw"
    )
    staff = create_staff(
        db, tenant_id=tenant.id, business_id=business.id, name="Marek"
    )
    svc = create_service(
        db, tenant_id=tenant.id, business_id=business.id, name="Haircut", duration_minutes=30
    )
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=business.id, phone="+48600100200"
    )
    return {
        "tenant_id": tenant.id,
        "business_id": business.id,
        "staff_id": staff.id,
        "service_id": svc.id,
        "customer_id": customer.id,
    }


# ── AVS-C001: slot generation from working hours ────────────────────────────

def test_no_working_hours_returns_empty(db, domain):
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert slots == []


def test_slots_generated_from_working_hours(db, domain):
    # Wednesday = weekday 2, 09:00–11:00 Warsaw → 2 slots of 30 min
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(11, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 4  # 09:00, 09:30, 10:00, 10:30


def test_slot_ends_at_is_duration_after_starts_at(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 2
    for starts_at, ends_at in slots:
        assert ends_at - starts_at == timedelta(minutes=30)


def test_last_slot_fits_before_window_end(db, domain):
    # 1-hour service, 90-min window → only 1 slot (not 2)
    svc_long = create_service(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        name="Long service",
        duration_minutes=60,
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 30),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=svc_long.id,
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 1
    assert slots[0][0].hour == 7  # 09:00 Warsaw = 07:00 UTC (UTC+2 in July)


# ── AVS-C004: timezone handling ─────────────────────────────────────────────

def test_slots_converted_to_utc(db, domain):
    # Warsaw is UTC+2 in summer; 09:00 local = 07:00 UTC
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 2
    first_start, _ = slots[0]
    assert first_start.tzinfo is not None
    assert first_start == datetime(2027, 7, 7, 7, 0, 0, tzinfo=timezone.utc)


def test_winter_timezone_offset(db, domain):
    # January 2027 is UTC+1 in Warsaw; 09:00 local = 08:00 UTC
    winter_date = date(2027, 1, 6)  # Wednesday
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=winter_date,
    )
    assert len(slots) == 2
    first_start, _ = slots[0]
    assert first_start == datetime(2027, 1, 6, 8, 0, 0, tzinfo=timezone.utc)


# ── AVS-C002: exclude existing bookings ─────────────────────────────────────

def test_confirmed_booking_removes_slot(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    # Book 09:00 Warsaw = 07:00 UTC
    create_booking(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        customer_id=domain["customer_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        starts_at=datetime(2027, 7, 7, 7, 0, 0, tzinfo=timezone.utc),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    # 09:00 slot taken, only 09:30 remains
    assert len(slots) == 1
    assert slots[0][0] == datetime(2027, 7, 7, 7, 30, 0, tzinfo=timezone.utc)


def test_pending_payment_hold_removes_slot(db, domain):
    """ADR 0004 SS3: a PENDING_PAYMENT hold must reserve the slot in
    availability search too, not just the create-time double-booking
    guard -- otherwise availability/IVR would keep showing a held slot as
    free until a 409 at create time."""
    from app.services.booking_service import create_pending_payment_hold
    from app.services.service_service import update_service

    update_service(
        db,
        domain["service_id"],
        domain["business_id"],
        domain["tenant_id"],
        price_minor_units=5000,
        currency="PLN",
    )
    svc = require_service(db, domain["service_id"], domain["tenant_id"])
    svc.deposit_required = True
    svc.deposit_minor_units = 1000
    db.commit()

    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    create_pending_payment_hold(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        customer_id=domain["customer_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        starts_at=datetime(2027, 7, 7, 7, 0, 0, tzinfo=timezone.utc),
        provider="stripe",
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 1
    assert slots[0][0] == datetime(2027, 7, 7, 7, 30, 0, tzinfo=timezone.utc)


def test_cancelled_booking_does_not_block_slot(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    booking = create_booking(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        customer_id=domain["customer_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        starts_at=datetime(2027, 7, 7, 7, 0, 0, tzinfo=timezone.utc),
    )
    cancel_booking(db, booking.id, domain["business_id"], domain["tenant_id"], reason="test")

    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 2  # Both slots available again


def test_fully_booked_returns_empty(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    for starts_utc in [
        datetime(2027, 7, 7, 7, 0, 0, tzinfo=timezone.utc),
        datetime(2027, 7, 7, 7, 30, 0, tzinfo=timezone.utc),
    ]:
        create_booking(
            db,
            tenant_id=domain["tenant_id"],
            business_id=domain["business_id"],
            customer_id=domain["customer_id"],
            service_id=domain["service_id"],
            staff_id=domain["staff_id"],
            starts_at=starts_utc,
        )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert slots == []


# ── AVS-C003: availability exceptions ───────────────────────────────────────

def test_closed_exception_returns_empty(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        exception_date=FUTURE_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="Holiday",
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert slots == []


def test_special_hours_exception_overrides_working_hours(db, domain):
    # Working hours: 09:00–17:00 (16 slots of 30 min)
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    # Exception: only 09:00–10:00 available
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        exception_date=FUTURE_DATE,
        is_closed=False,
        start_time=time(9, 0),
        end_time=time(10, 0),
        reason="Short day",
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 2  # Only 09:00 and 09:30


def test_business_wide_closed_exception_blocks_staff_slots(db, domain):
    # Business-level (staff_id=None) exception should block staff slots too
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    create_availability_exception(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,  # business-wide
        exception_date=FUTURE_DATE,
        is_closed=True,
        start_time=None,
        end_time=None,
        reason="National holiday",
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert slots == []


# ── P3-002: salon/staff hours intersection ──────────────────────────────────

def test_staff_without_own_hours_falls_back_to_salon_hours(db, domain):
    """A staff member with no staff-specific WorkingHours override follows
    the salon's business-wide hours, not an empty schedule."""
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 16  # 8 hours / 30 min


def test_staff_specific_hours_narrower_than_salon_get_intersected(db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(13, 0),
        end_time=time(15, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 4  # 2 hours / 30 min, not the salon's full 8 hours
    starts_at, _ = slots[0]
    assert starts_at.astimezone(timezone(timedelta(hours=2))).time() == time(13, 0)


def test_staff_specific_hours_wider_than_salon_get_clipped(db, domain):
    """A staff member can't take bookings outside the salon's own hours,
    even if their personal schedule would otherwise allow it."""
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(6, 0),
        end_time=time(20, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 6  # clipped to the salon's 9:00-12:00, not 6:00-20:00


def test_staff_hours_used_as_is_when_salon_has_no_business_wide_hours(db, domain):
    """Preserves pre-P3-002 behavior for a business that only ever
    configures per-staff hours and never sets up business-wide ones."""
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert len(slots) == 16  # the staff's own 8-hour window, unmodified


def test_no_salon_and_no_staff_hours_returns_empty(db, domain):
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    assert slots == []


def test_split_shift_intersection_handles_multiple_windows_per_side(db, domain):
    """Either side of the intersection may have more than one window (e.g.
    a split shift) -- every pairwise overlap must be considered, not just
    a 1:1 zip of the two lists."""
    for start, end in [(time(9, 0), time(12, 0)), (time(15, 0), time(18, 0))]:
        create_working_hours(
            db,
            tenant_id=domain["tenant_id"],
            business_id=domain["business_id"],
            staff_id=None,
            day_of_week=2,
            start_time=start,
            end_time=end,
        )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(11, 0),
        end_time=time(16, 0),
    )
    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,
    )
    # Intersected windows: 11:00-12:00 (1h) and 15:00-16:00 (1h) -> 4 slots of 30 min
    assert len(slots) == 4


def test_staff_with_managed_schedule_is_closed_on_an_unconfigured_day(db, domain):
    """A staff member with their own hours on some days (e.g. Mon-Fri) must
    NOT fall back to the salon's hours on a day they have no row for --
    that fallback is only for a staff member with zero rows of their own,
    not a day-by-day gap in an otherwise-managed schedule."""
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=2,  # salon is open Wednesday (FUTURE_DATE)
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=1,  # this staff member only works Tuesdays
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,  # Wednesday -- not one of this staff's days
    )

    assert slots == []


def test_salon_with_managed_schedule_is_closed_on_an_unconfigured_day_even_if_staff_has_hours(db, domain):
    """The same bug, mirrored on the salon side: a business with its own
    managed schedule on some days (e.g. Mon-Fri) must NOT let a staff
    member's hours on a day the salon has no row for stand in for "salon
    open" -- the salon is implicitly closed that day, same as a staff
    member would be."""
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=None,
        day_of_week=1,  # salon only opens Tuesdays
        start_time=time(9, 0),
        end_time=time(17, 0),
    )
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,  # this staff member works Wednesdays (FUTURE_DATE)
        start_time=time(9, 0),
        end_time=time(17, 0),
    )

    slots = get_available_slots(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        service_id=domain["service_id"],
        staff_id=domain["staff_id"],
        query_date=FUTURE_DATE,  # Wednesday -- not one of the salon's days
    )

    assert slots == []


# ── AVS-C005: Availability API ───────────────────────────────────────────────

def test_api_availability_requires_auth(client, db, domain):
    create_working_hours(
        db,
        tenant_id=domain["tenant_id"],
        business_id=domain["business_id"],
        staff_id=domain["staff_id"],
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )
    resp = client.get(
        f"/api/v1/businesses/{domain['business_id']}/availability",
        params={"service_id": domain["service_id"], "date": str(FUTURE_DATE)},
    )
    assert resp.status_code == 401


def test_api_availability_returns_slots(db, client):
    register_user(client, "avail1@example.com")
    promote_to_admin(db, "avail1@example.com")
    token = login_user(client, "avail1@example.com").json()["access_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="API Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Anna")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    create_working_hours(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        staff_id=staff.id,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(10, 0),
    )

    resp = client.get(
        f"/api/v1/businesses/{biz.id}/availability",
        params={"service_id": svc.id, "staff_id": staff.id, "date": str(FUTURE_DATE)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    slots = resp.json()
    assert len(slots) == 2
    assert "starts_at" in slots[0]
    assert "ends_at" in slots[1]


def test_api_availability_unknown_business_returns_404(db, client):
    register_user(client, "avail2@example.com")
    token = login_user(client, "avail2@example.com").json()["access_token"]
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    svc = create_service(
        db,
        tenant_id=tenant.id,
        business_id=create_business(db, tenant_id=tenant.id, name="X", timezone="UTC").id,
        name="Y",
        duration_minutes=30,
    )

    resp = client.get(
        "/api/v1/businesses/99999/availability",
        params={"service_id": svc.id, "date": str(FUTURE_DATE)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 404


def test_api_availability_missing_required_params_returns_422(db, client):
    register_user(client, "avail3@example.com")
    token = login_user(client, "avail3@example.com").json()["access_token"]
    resp = client.get(
        "/api/v1/businesses/1/availability",
        headers=auth_headers(token),
    )
    assert resp.status_code == 422

