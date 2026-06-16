"""Tests for the calendar event model (AVS-F003)."""

import pytest

from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.calendar_event import CalendarEvent, CalendarSyncStatus
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff


_STARTS_AT = datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="CalEv Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600100300")
    # Insert booking directly to avoid auto-creating a CalendarEvent via create_booking.
    booking = Booking(
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
        ends_at=_STARTS_AT + timedelta(minutes=30),
        status=BookingStatus.CONFIRMED,
        source=BookingSource.API,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return tenant.id, biz.id, booking.id


def test_calendar_event_persists_with_defaults(db):
    tenant_id, biz_id, booking_id = _setup(db)

    event = CalendarEvent(
        tenant_id=tenant_id,
        business_id=biz_id,
        booking_id=booking_id,
        provider="fake",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    assert event.id is not None
    assert event.status == CalendarSyncStatus.PENDING
    assert event.attempts == 0
    assert event.provider_event_id is None
    assert event.synced_at is None
    assert event.last_error is None
    assert event.created_at is not None


def test_calendar_event_unique_per_booking(db):
    tenant_id, biz_id, booking_id = _setup(db)

    db.add(CalendarEvent(tenant_id=tenant_id, business_id=biz_id, booking_id=booking_id, provider="fake"))
    db.commit()

    db.add(CalendarEvent(tenant_id=tenant_id, business_id=biz_id, booking_id=booking_id, provider="fake"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_calendar_event_lifecycle_to_synced(db):
    tenant_id, biz_id, booking_id = _setup(db)

    event = CalendarEvent(
        tenant_id=tenant_id, business_id=biz_id, booking_id=booking_id, provider="fake"
    )
    db.add(event)
    db.commit()

    event.status = CalendarSyncStatus.SYNCED
    event.provider_event_id = "fake-evt-001"
    event.attempts = 1
    event.synced_at = datetime(2027, 9, 1, 8, 0, tzinfo=timezone.utc)
    db.commit()
    db.refresh(event)

    assert event.status == CalendarSyncStatus.SYNCED
    assert event.provider_event_id == "fake-evt-001"
    assert event.synced_at is not None


def test_calendar_event_lifecycle_to_failed(db):
    tenant_id, biz_id, booking_id = _setup(db)

    event = CalendarEvent(
        tenant_id=tenant_id, business_id=biz_id, booking_id=booking_id, provider="fake"
    )
    db.add(event)
    db.commit()

    event.status = CalendarSyncStatus.FAILED
    event.attempts = 3
    event.last_error = "provider_timeout"
    db.commit()
    db.refresh(event)

    assert event.status == CalendarSyncStatus.FAILED
    assert event.last_error == "provider_timeout"


def test_calendar_event_query_scoped_to_tenant(db):
    tenant_id, biz_id, booking_id = _setup(db)

    other_tenant = Tenant(slug="calev-other", name="Other", is_active=True)
    db.add(other_tenant)
    db.commit()
    db.refresh(other_tenant)

    db.add(CalendarEvent(tenant_id=tenant_id, business_id=biz_id, booking_id=booking_id, provider="fake"))
    db.commit()

    results = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.tenant_id == other_tenant.id)
        .all()
    )
    assert results == []
