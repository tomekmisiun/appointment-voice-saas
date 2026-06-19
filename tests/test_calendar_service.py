"""Tests for calendar event enqueue and sync worker (AVS-F005)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.booking import Booking, BookingSource, BookingStatus
from app.models.calendar_event import CalendarEvent, CalendarSyncStatus
from app.models.calendar_integration import CalendarIntegration
from app.models.tenant import Tenant  # used in _setup
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.calendar_provider import FakeCalendarProvider
from app.services.calendar_service import (
    CalendarCancelError,
    CalendarSyncError,
    cancel_calendar_event_in_worker,
    enqueue_calendar_event,
    get_calendar_event_for_booking,
    sync_calendar_event_in_worker,
)
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff

_STARTS_AT = datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Cal Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Ola")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600200300")
    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )
    return tenant.id, biz, svc, staff, booking


def _bare_booking(db, *, tenant_id, biz, svc, staff, starts_at):
    """Insert a booking without triggering the booking service side-effects."""
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48600299001"
    )
    booking = Booking(
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=svc.duration_minutes),
        status=BookingStatus.CONFIRMED,
        source=BookingSource.API,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def test_enqueue_calendar_event_creates_pending_record(db):
    tenant_id, biz, svc, staff, _booking = _setup(db)
    bare = _bare_booking(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff=staff,
        starts_at=datetime(2027, 9, 3, 9, 0, tzinfo=timezone.utc),
    )

    event = enqueue_calendar_event(db, booking=bare, business=biz)
    db.commit()

    assert event.id is not None
    assert event.status == CalendarSyncStatus.PENDING
    assert event.booking_id == bare.id
    assert event.tenant_id == tenant_id
    assert event.provider == "null"


def test_enqueue_calendar_event_uses_integration_provider(db):
    tenant_id, biz, svc, staff, _booking = _setup(db)

    db.add(CalendarIntegration(
        tenant_id=tenant_id,
        business_id=biz.id,
        provider="fake",
        is_active=True,
    ))
    db.commit()

    bare = _bare_booking(
        db, tenant_id=tenant_id, biz=biz, svc=svc, staff=staff,
        starts_at=datetime(2027, 9, 4, 10, 0, tzinfo=timezone.utc),
    )

    event = enqueue_calendar_event(db, booking=bare, business=biz)
    db.commit()

    assert event.provider == "fake"


def test_create_booking_enqueues_calendar_event(db):
    tenant_id, biz, _svc, _staff, booking = _setup(db)

    cal_events = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.booking_id == booking.id)
        .all()
    )
    assert len(cal_events) == 1
    assert cal_events[0].status == CalendarSyncStatus.PENDING


def test_sync_calendar_event_succeeds_with_fake_provider(db):
    _tenant_id, biz, svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    provider = FakeCalendarProvider()

    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    db.refresh(event)
    assert event.status == CalendarSyncStatus.SYNCED
    assert event.provider_event_id == "fake-evt-1"
    assert event.synced_at is not None
    assert event.attempts == 1
    assert len(provider.created) == 1


def test_sync_calendar_event_builds_title_with_staff(db):
    _tenant_id, biz, svc, staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    provider = FakeCalendarProvider()

    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    assert provider.created[0].title == "Cut – Ola"


def test_sync_calendar_event_increments_attempts_on_failure(db):
    _tenant_id, biz, svc, _staff, booking = _setup(db)

    class FailingProvider:
        def create_event(self, event):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

        def update_event(self, pid, event):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

        def cancel_event(self, pid):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()

    with pytest.raises(CalendarSyncError):
        sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=FailingProvider())

    db.refresh(event)
    assert event.attempts == 1
    assert event.last_error == "provider_timeout"
    assert event.status == CalendarSyncStatus.PENDING


def test_sync_calendar_event_marks_failed_after_max_attempts(db):
    _tenant_id, biz, svc, _staff, booking = _setup(db)

    class FailingProvider:
        def create_event(self, event):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

        def update_event(self, pid, event):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

        def cancel_event(self, pid):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="provider_timeout")

    from app.core.config import settings

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    event.attempts = settings.worker_max_retries - 1
    db.commit()

    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=FailingProvider())

    db.refresh(event)
    assert event.status == CalendarSyncStatus.FAILED
    assert event.attempts == settings.worker_max_retries


def test_sync_calendar_event_skips_already_synced(db):
    _tenant_id, biz, svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    event.status = CalendarSyncStatus.SYNCED
    event.provider_event_id = "existing-evt"
    db.commit()

    provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    assert provider.created == []


def test_sync_calendar_event_scoped_to_tenant(db):
    tenant_id, biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    db.refresh(event)
    assert event.tenant_id == tenant_id


# AVS-F006: cancel/update calendar event on booking cancellation


def test_cancel_booking_enqueues_cancel_calendar_event(db, monkeypatch):
    import app.services.booking_service as bk_svc
    from app.services.booking_service import cancel_booking

    _tenant_id, _biz, _svc, _staff, booking = _setup(db)
    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()

    enqueued_ids = []
    monkeypatch.setattr(bk_svc, "enqueue_cancel_calendar_event_job", lambda eid: enqueued_ids.append(eid))

    cancel_booking(db, booking.id, booking.business_id, booking.tenant_id)

    assert enqueued_ids == [event.id]


def test_cancel_booking_handles_missing_calendar_event(db, monkeypatch):
    from datetime import timedelta
    from app.models.booking import Booking, BookingSource, BookingStatus
    import app.services.booking_service as bk_svc
    from app.services.booking_service import cancel_booking

    tenant_id, biz, svc, staff, _existing_booking = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48600399001")
    starts = datetime(2027, 9, 5, 9, 0, tzinfo=timezone.utc)
    bare = Booking(
        tenant_id=tenant_id, business_id=biz.id, customer_id=customer.id,
        service_id=svc.id, staff_id=staff.id,
        starts_at=starts, ends_at=starts + timedelta(minutes=30),
        status=BookingStatus.CONFIRMED, source=BookingSource.API,
    )
    db.add(bare)
    db.commit()
    db.refresh(bare)

    enqueued_ids = []
    monkeypatch.setattr(bk_svc, "enqueue_cancel_calendar_event_job", lambda eid: enqueued_ids.append(eid))

    cancel_booking(db, bare.id, bare.business_id, bare.tenant_id)

    assert enqueued_ids == []  # no CalendarEvent row → nothing enqueued


def test_cancel_calendar_event_pending_marks_cancelled_without_provider(db):
    _tenant_id, _biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    assert event.status == CalendarSyncStatus.PENDING

    provider = FakeCalendarProvider()
    cancel_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    db.refresh(event)
    assert event.status == CalendarSyncStatus.CANCELLED
    assert provider.cancelled == []


def test_cancel_calendar_event_synced_calls_provider(db):
    _tenant_id, _biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)
    db.refresh(event)
    assert event.status == CalendarSyncStatus.SYNCED

    cancel_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    db.refresh(event)
    assert event.status == CalendarSyncStatus.CANCELLED
    assert provider.cancelled == [event.provider_event_id]


def test_cancel_calendar_event_already_cancelled_is_noop(db):
    _tenant_id, _biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    event.status = CalendarSyncStatus.CANCELLED
    db.commit()

    provider = FakeCalendarProvider()
    cancel_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    assert provider.cancelled == []


def test_cancel_calendar_event_failed_marks_cancelled_without_provider(db):
    _tenant_id, _biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    event.status = CalendarSyncStatus.FAILED
    event.last_error = "previous_timeout"
    db.commit()

    provider = FakeCalendarProvider()
    cancel_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    db.refresh(event)
    assert event.status == CalendarSyncStatus.CANCELLED
    assert provider.cancelled == []


def test_cancel_calendar_event_synced_retries_on_provider_failure(db):
    _tenant_id, _biz, _svc, _staff, booking = _setup(db)

    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)
    db.refresh(event)

    class FailingProvider:
        def create_event(self, e):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="timeout")

        def update_event(self, pid, e):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="timeout")

        def cancel_event(self, pid):
            from app.core.calendar import CalendarResult
            return CalendarResult(success=False, error="timeout")

    with pytest.raises(CalendarCancelError):
        cancel_calendar_event_in_worker(db, event_id=event.id, calendar_provider=FailingProvider())

    db.refresh(event)
    assert event.status == CalendarSyncStatus.SYNCED
    assert event.last_error == "timeout"
    assert event.cancel_attempts == 1


def test_get_calendar_event_for_booking_returns_none_when_absent(db):
    tenant_id, _biz, _svc, _staff, booking = _setup(db)

    result = get_calendar_event_for_booking(db, booking_id=999999, tenant_id=tenant_id)

    assert result is None


def test_get_calendar_event_for_booking_is_tenant_scoped(db):
    tenant_id, _biz, _svc, _staff, booking = _setup(db)

    result = get_calendar_event_for_booking(db, booking_id=booking.id, tenant_id=9999999)

    assert result is None
