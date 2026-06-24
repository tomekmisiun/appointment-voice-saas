"""Tests for the P3-013 integration reconciliation sweep."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.job_queue import Job, queue_name_for_job_type
from app.core.redis import redis_client
from app.models.calendar_event import CalendarSyncStatus
from app.models.notification_outbox import (
    NotificationChannel,
    NotificationOutbox,
    NotificationPurpose,
    NotificationStatus,
)
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.calendar_service import SYNC_CALENDAR_EVENT_JOB, get_calendar_event_for_booking
from app.services.customer_service import get_or_create_customer
from app.services.notification_service import SEND_NOTIFICATION_JOB
from app.services.reconciliation_service import (
    CALENDAR_EVENT_RECORD_TYPE,
    NOTIFICATION_RECORD_TYPE,
    reconcile_stale_calendar_events,
    reconcile_stale_notifications,
)
from app.services.booking_service import create_booking
from app.services.service_service import create_service
from app.services.staff_service import create_staff

_STARTS_AT = datetime(2027, 9, 1, 9, 0, tzinfo=timezone.utc)
_STALE_MINUTES = 15


@pytest.fixture(autouse=True)
def _clean_job_queues():
    # Real per-job-type Redis queues are shared across the whole test
    # session (not flushed between tests, see test_worker.py's own note on
    # this) -- clear before and after so this file neither inherits nor
    # leaves behind residue for unrelated tests like the round-robin
    # fairness check in test_worker.py.
    queues = [
        queue_name_for_job_type(SEND_NOTIFICATION_JOB),
        queue_name_for_job_type(SYNC_CALENDAR_EVENT_JOB),
    ]
    redis_client.delete(*queues)
    yield
    redis_client.delete(*queues)


def _setup_business(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Reconcile Salon", timezone="Europe/Warsaw")
    return tenant.id, biz


def _make_notification(db, *, tenant_id, business_id, status, created_at):
    intent = NotificationOutbox(
        tenant_id=tenant_id,
        business_id=business_id,
        channel=NotificationChannel.SMS,
        purpose=NotificationPurpose.BOOKING_CONFIRMATION,
        recipient_phone="+48600100200",
        body="Your booking is confirmed.",
        status=status,
        created_at=created_at,
    )
    db.add(intent)
    db.commit()
    db.refresh(intent)
    return intent


def _make_booking(db, *, tenant_id, biz, starts_at):
    staff = create_staff(db, tenant_id=tenant_id, business_id=biz.id, name="Ola")
    svc = create_service(db, tenant_id=tenant_id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48600200300"
    )
    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=starts_at,
    )


def _make_calendar_event(db, *, tenant_id, biz, status, created_at, starts_at):
    # create_booking() already creates a CalendarEvent (and a confirmation
    # NotificationOutbox pair) as a side effect -- fetch and mutate that one
    # instead of calling enqueue_calendar_event() again, which would collide
    # with the booking_id unique constraint.
    booking = _make_booking(db, tenant_id=tenant_id, biz=biz, starts_at=starts_at)
    event = get_calendar_event_for_booking(db, booking.id, tenant_id)
    event.status = status
    event.created_at = created_at
    db.commit()
    db.refresh(event)
    return event


def _clear_queue(job_type):
    redis_client.delete(queue_name_for_job_type(job_type))


def _read_queue(job_type):
    queue_name = queue_name_for_job_type(job_type)
    raw_jobs = redis_client.lrange(queue_name, 0, -1)
    return [Job.from_json(raw) for raw in raw_jobs]


def test_reconcile_stale_notifications_requeues_old_pending_rows(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=_STALE_MINUTES + 1)
    intent = _make_notification(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        status=NotificationStatus.PENDING,
        created_at=stale_created_at,
    )
    _clear_queue(SEND_NOTIFICATION_JOB)

    count = reconcile_stale_notifications(db)

    assert count == 1
    jobs = _read_queue(SEND_NOTIFICATION_JOB)
    assert intent.id in {job.payload["notification_id"] for job in jobs}


def test_reconcile_stale_notifications_leaves_recent_pending_rows_untouched(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    recent_created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    _make_notification(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        status=NotificationStatus.PENDING,
        created_at=recent_created_at,
    )
    _clear_queue(SEND_NOTIFICATION_JOB)

    count = reconcile_stale_notifications(db)

    assert count == 0
    assert _read_queue(SEND_NOTIFICATION_JOB) == []


def test_reconcile_stale_notifications_ignores_terminal_rows(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=_STALE_MINUTES + 1)
    _make_notification(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        status=NotificationStatus.SENT,
        created_at=stale_created_at,
    )
    _make_notification(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        status=NotificationStatus.FAILED,
        created_at=stale_created_at,
    )
    _clear_queue(SEND_NOTIFICATION_JOB)

    count = reconcile_stale_notifications(db)

    assert count == 0
    assert _read_queue(SEND_NOTIFICATION_JOB) == []


def test_reconcile_stale_calendar_events_requeues_pending_and_failed(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=_STALE_MINUTES + 1)
    pending_event = _make_calendar_event(
        db,
        tenant_id=tenant_id,
        biz=biz,
        status=CalendarSyncStatus.PENDING,
        created_at=stale_created_at,
        starts_at=_STARTS_AT,
    )
    failed_event = _make_calendar_event(
        db,
        tenant_id=tenant_id,
        biz=biz,
        status=CalendarSyncStatus.FAILED,
        created_at=stale_created_at,
        starts_at=_STARTS_AT + timedelta(hours=1),
    )
    _clear_queue(SYNC_CALENDAR_EVENT_JOB)

    count = reconcile_stale_calendar_events(db)

    assert count == 2
    jobs = _read_queue(SYNC_CALENDAR_EVENT_JOB)
    assert {pending_event.id, failed_event.id} <= {job.payload["event_id"] for job in jobs}


def test_reconcile_stale_calendar_events_leaves_recent_rows_untouched(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    recent_created_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    _make_calendar_event(
        db,
        tenant_id=tenant_id,
        biz=biz,
        status=CalendarSyncStatus.PENDING,
        created_at=recent_created_at,
        starts_at=_STARTS_AT,
    )
    _clear_queue(SYNC_CALENDAR_EVENT_JOB)

    count = reconcile_stale_calendar_events(db)

    assert count == 0
    assert _read_queue(SYNC_CALENDAR_EVENT_JOB) == []


def test_reconcile_stale_calendar_events_ignores_synced_and_cancelled_rows(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    tenant_id, biz = _setup_business(db)
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=_STALE_MINUTES + 1)
    _make_calendar_event(
        db,
        tenant_id=tenant_id,
        biz=biz,
        status=CalendarSyncStatus.SYNCED,
        created_at=stale_created_at,
        starts_at=_STARTS_AT,
    )
    _make_calendar_event(
        db,
        tenant_id=tenant_id,
        biz=biz,
        status=CalendarSyncStatus.CANCELLED,
        created_at=stale_created_at,
        starts_at=_STARTS_AT + timedelta(hours=1),
    )
    _clear_queue(SYNC_CALENDAR_EVENT_JOB)

    count = reconcile_stale_calendar_events(db)

    assert count == 0
    assert _read_queue(SYNC_CALENDAR_EVENT_JOB) == []


def test_reconcile_stale_notifications_emits_requeued_metric(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    observed = []
    monkeypatch.setattr(
        "app.services.reconciliation_service.observe_integration_reconciliation_requeued",
        lambda **kwargs: observed.append(kwargs),
    )
    tenant_id, biz = _setup_business(db)
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=_STALE_MINUTES + 1)
    _make_notification(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        status=NotificationStatus.PENDING,
        created_at=stale_created_at,
    )

    reconcile_stale_notifications(db)

    assert observed == [{"record_type": NOTIFICATION_RECORD_TYPE, "count": 1}]


def test_reconcile_stale_calendar_events_emits_requeued_metric_even_when_zero(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.reconciliation_service.settings.worker_reconciliation_stale_minutes",
        _STALE_MINUTES,
    )
    observed = []
    monkeypatch.setattr(
        "app.services.reconciliation_service.observe_integration_reconciliation_requeued",
        lambda **kwargs: observed.append(kwargs),
    )

    reconcile_stale_calendar_events(db)

    assert observed == [{"record_type": CALENDAR_EVENT_RECORD_TYPE, "count": 0}]
