from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import observe_integration_reconciliation_requeued
from app.models.calendar_event import CalendarEvent, CalendarSyncStatus
from app.models.notification_outbox import NotificationOutbox, NotificationStatus
from app.services.calendar_service import enqueue_sync_calendar_event_job
from app.services.notification_service import enqueue_send_notification_job

NOTIFICATION_RECORD_TYPE = "notification"
CALENDAR_EVENT_RECORD_TYPE = "calendar_event"


def _stale_threshold() -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        minutes=settings.worker_reconciliation_stale_minutes
    )


def reconcile_stale_notifications(db: Session, *, now: datetime | None = None) -> int:
    """Re-enqueue a fresh job for NotificationOutbox rows stuck PENDING past
    the staleness threshold -- the gap this closes is the job enqueue to
    Redis happening as a separate step after the DB commit, which can be
    lost (crash, transient Redis failure) leaving no job ever processing the
    row. FAILED rows are deliberately not touched: send_notification_in_worker
    hard-returns unless status == PENDING, so re-queueing one is a no-op.

    Gated on COALESCE(reconciled_at, created_at) rather than created_at alone
    so a row already re-queued by a previous sweep isn't re-queued again on
    every subsequent maintenance tick while the original requeued job may
    still be legitimately in flight -- caught by cross-provider review, which
    flagged the created_at-only version as a duplicate-send risk."""
    current_time = now or datetime.now(timezone.utc)
    last_touched = func.coalesce(
        NotificationOutbox.reconciled_at, NotificationOutbox.created_at
    )
    stale = (
        db.query(NotificationOutbox)
        .filter(
            NotificationOutbox.status == NotificationStatus.PENDING,
            last_touched < current_time - timedelta(
                minutes=settings.worker_reconciliation_stale_minutes
            ),
        )
        .all()
    )

    for intent in stale:
        enqueue_send_notification_job(intent.id)
        intent.reconciled_at = current_time

    if stale:
        db.commit()

    observe_integration_reconciliation_requeued(
        record_type=NOTIFICATION_RECORD_TYPE, count=len(stale)
    )
    return len(stale)


def reconcile_stale_calendar_events(db: Session, *, now: datetime | None = None) -> int:
    """Re-enqueue a fresh sync job for CalendarEvent rows stuck PENDING or
    FAILED past the staleness threshold. FAILED is included (unlike the
    notification case) because sync_calendar_event_in_worker itself treats
    PENDING and FAILED as equally retryable on a fresh job -- this just gives
    a permanently-stuck row one more attempt per sweep, surfaced via the
    reconciliation metric. Gated on COALESCE(reconciled_at, created_at), same
    as notifications, so a row already re-queued this sweep cycle isn't
    re-queued again every tick -- a row that keeps failing forever still gets
    retried, just at most once per worker_reconciliation_stale_minutes window
    instead of once per (typically much shorter) maintenance interval."""
    current_time = now or datetime.now(timezone.utc)
    last_touched = func.coalesce(CalendarEvent.reconciled_at, CalendarEvent.created_at)
    stale = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.status.in_(
                [CalendarSyncStatus.PENDING, CalendarSyncStatus.FAILED]
            ),
            last_touched < current_time - timedelta(
                minutes=settings.worker_reconciliation_stale_minutes
            ),
        )
        .all()
    )

    for event in stale:
        enqueue_sync_calendar_event_job(event.id)
        event.reconciled_at = current_time

    if stale:
        db.commit()

    observe_integration_reconciliation_requeued(
        record_type=CALENDAR_EVENT_RECORD_TYPE, count=len(stale)
    )
    return len(stale)
