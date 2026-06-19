"""Tests for Availability engine (AVS-C001–AVS-C006)."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.models.tenant import Tenant
from app.services.availability_service import get_available_slots
from app.services.availability_exception_service import create_availability_exception
from app.services.booking_service import create_booking, cancel_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
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

