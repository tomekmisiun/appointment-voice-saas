"""P2-009: combined-duration availability search.

Adds get_available_slots_for_total_duration(), a sibling of
get_available_slots() that searches for a combined duration across
multiple services (built from P2-008's BookingLineItem rows) instead of a
single service_id's duration_minutes. The single-service function and its
existing call sites (IVR, availability API) are untouched -- both share
the same private slot-generation core, parameterized by duration.
"""
from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.core.domain_errors import NotFoundError
from app.models.tenant import Tenant
from app.services.availability_service import (
    get_available_slots,
    get_available_slots_for_total_duration,
)
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.services.working_hours_service import create_working_hours


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Combined Duration Salon", timezone="UTC")
    haircut = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    color = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Color", duration_minutes=60
    )
    for day in range(7):
        create_working_hours(
            db,
            tenant_id=tenant.id,
            business_id=biz.id,
            staff_id=None,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(11, 0),
        )
    return tenant.id, biz, haircut, color


def _next_matching_weekday(weekday: int) -> date:
    today = date.today()
    offset = (weekday - today.weekday()) % 7
    return today + timedelta(days=offset)


def test_combined_duration_produces_fewer_wider_slots_than_single_service(db):
    tenant_id, biz, haircut, color = _setup(db)
    query_date = _next_matching_weekday(0)

    single_service_slots = get_available_slots(
        db, tenant_id=tenant_id, business_id=biz.id, service_id=haircut.id,
        staff_id=None, query_date=query_date,
    )
    combined_slots = get_available_slots_for_total_duration(
        db, tenant_id=tenant_id, business_id=biz.id, total_duration_minutes=90,
        staff_id=None, query_date=query_date,
    )

    # 2-hour window: 30-min slots -> 4 slots; 90-min combined -> 1 slot
    assert len(single_service_slots) == 4
    assert len(combined_slots) == 1
    start, end = combined_slots[0]
    assert (end - start).total_seconds() / 60 == 90


def test_combined_duration_respects_existing_bookings(db):
    # 90-min slot generation steps by the duration itself (grid-aligned),
    # so a 4-hour window yields two 90-min candidates: 9:00-10:30 and
    # 10:30-12:00 (12:00-13:30 would overrun the window and isn't offered).
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Wide Window Salon", timezone="UTC")
    haircut = create_service(
        db, tenant_id=tenant.id, business_id=biz.id, name="Haircut", duration_minutes=30
    )
    for day in range(7):
        create_working_hours(
            db, tenant_id=tenant.id, business_id=biz.id, staff_id=None,
            day_of_week=day, start_time=time(9, 0), end_time=time(13, 0),
        )
    query_date = _next_matching_weekday(1)

    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz.id, phone="+48730000001", name="Booked"
    )
    starts_at = datetime.combine(query_date, time(9, 0), tzinfo=timezone.utc)
    create_booking(
        db, tenant_id=tenant.id, business_id=biz.id, customer_id=customer.id,
        service_id=haircut.id, staff_id=None, starts_at=starts_at,
    )

    combined_slots = get_available_slots_for_total_duration(
        db, tenant_id=tenant.id, business_id=biz.id, total_duration_minutes=90,
        staff_id=None, query_date=query_date,
    )

    # the 9:00-10:30 candidate overlaps the 9:00-9:30 booking and is
    # excluded, leaving only the 10:30-12:00 slot.
    assert len(combined_slots) == 1
    start, end = combined_slots[0]
    assert start == starts_at + timedelta(minutes=90)
    assert end == starts_at + timedelta(minutes=180)


def test_combined_duration_returns_empty_when_no_working_hours(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="No Hours Salon", timezone="UTC")

    slots = get_available_slots_for_total_duration(
        db, tenant_id=tenant.id, business_id=biz.id, total_duration_minutes=90,
        staff_id=None, query_date=_next_matching_weekday(0),
    )

    assert slots == []


def test_combined_duration_filters_by_staff_working_hours(db):
    tenant_id, biz, haircut, color = _setup(db)
    staff = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Stylist")
    query_date = _next_matching_weekday(2)

    # staff has no working hours configured -> no slots for that staff
    slots = get_available_slots_for_total_duration(
        db, tenant_id=tenant_id, business_id=biz.id, total_duration_minutes=90,
        staff_id=staff.id, query_date=query_date,
    )

    assert slots == []


def test_combined_duration_rejects_unknown_staff(db):
    tenant_id, biz, haircut, color = _setup(db)

    with pytest.raises(NotFoundError):
        get_available_slots_for_total_duration(
            db, tenant_id=tenant_id, business_id=biz.id, total_duration_minutes=90,
            staff_id=999999, query_date=_next_matching_weekday(0),
        )


def test_combined_duration_rejects_staff_from_another_business(db):
    tenant_id, biz, haircut, color = _setup(db)
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).one()
    other_biz = create_business(db, tenant_id=tenant.id, name="Other Salon", timezone="UTC")
    other_staff = create_staff(db, tenant_id=tenant.id, business_id=other_biz.id, name="Other Stylist")

    with pytest.raises(NotFoundError):
        get_available_slots_for_total_duration(
            db, tenant_id=tenant_id, business_id=biz.id, total_duration_minutes=90,
            staff_id=other_staff.id, query_date=_next_matching_weekday(0),
        )


def test_single_service_search_unaffected_by_new_function(db):
    tenant_id, biz, haircut, color = _setup(db)
    query_date = _next_matching_weekday(3)

    slots = get_available_slots(
        db, tenant_id=tenant_id, business_id=biz.id, service_id=haircut.id,
        staff_id=None, query_date=query_date,
    )

    assert len(slots) == 4
    for start, end in slots:
        assert (end - start).total_seconds() / 60 == 30
