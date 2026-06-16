"""Tests for calendar sync/cancel worker retry and DLQ behaviour (AVS-F007)."""

import pytest

from app.core.calendar import CalendarResult
from app.core.config import settings
from app.core.job_queue import Job
from app.models.calendar_event import CalendarEvent, CalendarSyncStatus
from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.calendar_provider import FakeCalendarProvider
from app.services.calendar_service import (
    CANCEL_CALENDAR_EVENT_JOB,
    SYNC_CALENDAR_EVENT_JOB,
    CalendarCancelError,
    CalendarSyncError,
    cancel_calendar_event_in_worker,
    sync_calendar_event_in_worker,
)
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from app.worker import handle_job

from datetime import datetime, timezone

_STARTS_AT = datetime(2027, 10, 1, 9, 0, tzinfo=timezone.utc)


class _FailingCalendarProvider:
    def create_event(self, event):
        return CalendarResult(success=False, error="provider_down")

    def update_event(self, pid, event):
        return CalendarResult(success=False, error="provider_down")

    def cancel_event(self, pid):
        return CalendarResult(success=False, error="provider_down")


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Cal Worker Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Barber")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600301400")
    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_STARTS_AT,
    )
    event = db.query(CalendarEvent).filter(CalendarEvent.booking_id == booking.id).one()
    return tenant.id, booking, event


# --- sync retry/DLQ ---

def test_sync_retries_update_last_error_each_attempt(db):
    _tenant_id, _booking, event = _setup(db)
    provider = _FailingCalendarProvider()

    for expected_attempts in range(1, settings.worker_max_retries):
        with pytest.raises(CalendarSyncError):
            sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)
        db.refresh(event)
        assert event.attempts == expected_attempts
        assert event.last_error == "provider_down"
        assert event.status == CalendarSyncStatus.PENDING


def test_sync_marks_failed_without_raising_at_max_retries(db):
    _tenant_id, _booking, event = _setup(db)
    event.attempts = settings.worker_max_retries - 1
    db.commit()

    sync_calendar_event_in_worker(
        db, event_id=event.id, calendar_provider=_FailingCalendarProvider()
    )

    db.refresh(event)
    assert event.status == CalendarSyncStatus.FAILED
    assert event.attempts == settings.worker_max_retries


def test_sync_skips_cancelled_event(db):
    _tenant_id, _booking, event = _setup(db)
    event.status = CalendarSyncStatus.CANCELLED
    db.commit()
    provider = FakeCalendarProvider()

    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=provider)

    assert provider.created == []
    db.refresh(event)
    assert event.status == CalendarSyncStatus.CANCELLED


# --- cancel retry/DLQ ---

def test_cancel_synced_raises_on_first_failure(db):
    _tenant_id, _booking, event = _setup(db)
    good_provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=good_provider)
    db.refresh(event)
    assert event.status == CalendarSyncStatus.SYNCED

    with pytest.raises(CalendarCancelError):
        cancel_calendar_event_in_worker(
            db, event_id=event.id, calendar_provider=_FailingCalendarProvider()
        )
    db.refresh(event)
    assert event.last_error == "provider_down"
    assert event.status == CalendarSyncStatus.SYNCED


def test_cancel_synced_leaves_synced_after_max_retries(db):
    _tenant_id, _booking, event = _setup(db)
    good_provider = FakeCalendarProvider()
    sync_calendar_event_in_worker(db, event_id=event.id, calendar_provider=good_provider)
    db.refresh(event)
    event.attempts = settings.worker_max_retries - 1
    db.commit()

    cancel_calendar_event_in_worker(
        db, event_id=event.id, calendar_provider=_FailingCalendarProvider()
    )

    db.refresh(event)
    assert event.status == CalendarSyncStatus.SYNCED
    assert event.last_error == "provider_down"
    assert event.attempts == settings.worker_max_retries


# --- worker dispatch ---

def test_handle_job_dispatches_sync_calendar_event_job(db, monkeypatch):
    _tenant_id, _booking, event = _setup(db)
    calls = []

    monkeypatch.setattr(
        "app.worker.sync_calendar_event_in_worker",
        lambda db, *, event_id: calls.append(event_id),
    )

    handle_job(Job(
        id="job-sync-1",
        type=SYNC_CALENDAR_EVENT_JOB,
        payload={"event_id": event.id},
        attempts=1,
    ))

    assert calls == [event.id]


def test_handle_job_dispatches_cancel_calendar_event_job(db, monkeypatch):
    _tenant_id, _booking, event = _setup(db)
    calls = []

    monkeypatch.setattr(
        "app.worker.cancel_calendar_event_in_worker",
        lambda db, *, event_id: calls.append(event_id),
    )

    handle_job(Job(
        id="job-cancel-1",
        type=CANCEL_CALENDAR_EVENT_JOB,
        payload={"event_id": event.id},
        attempts=1,
    ))

    assert calls == [event.id]
