from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.calendar import CalendarEvent as CalendarEventPayload
from app.core.config import settings
from app.core.job_queue import Job, enqueue_job
from app.models.booking import Booking
from app.models.business import Business
from app.models.calendar_event import CalendarEvent, CalendarSyncStatus
from app.models.calendar_integration import CalendarIntegration
from app.models.service import Service
from app.models.staff import Staff
from app.services.calendar_provider import CalendarProvider, get_calendar_provider

SYNC_CALENDAR_EVENT_JOB = "sync_calendar_event"
CANCEL_CALENDAR_EVENT_JOB = "cancel_calendar_event"


class CalendarSyncError(Exception):
    pass


class CalendarCancelError(Exception):
    pass


def enqueue_sync_calendar_event_job(event_id: int) -> Job:
    return enqueue_job(SYNC_CALENDAR_EVENT_JOB, {"event_id": event_id})


def enqueue_cancel_calendar_event_job(event_id: int) -> Job:
    return enqueue_job(CANCEL_CALENDAR_EVENT_JOB, {"event_id": event_id})


def _get_provider_name(db: Session, business_id: int, tenant_id: int) -> str:
    integration = (
        db.query(CalendarIntegration)
        .filter(
            CalendarIntegration.business_id == business_id,
            CalendarIntegration.tenant_id == tenant_id,
            CalendarIntegration.staff_id.is_(None),
            CalendarIntegration.is_active.is_(True),
        )
        .first()
    )
    return integration.provider if integration is not None else "null"


def enqueue_calendar_event(
    db: Session,
    *,
    booking: Booking,
    business: Business,
) -> CalendarEvent:
    provider_name = _get_provider_name(db, business.id, booking.tenant_id)
    event = CalendarEvent(
        tenant_id=booking.tenant_id,
        business_id=booking.business_id,
        booking_id=booking.id,
        provider=provider_name,
    )
    db.add(event)
    db.flush()
    return event


def _build_event_payload(
    booking: Booking, service: Service, staff: Staff | None
) -> CalendarEventPayload:
    title_parts = [service.name]
    if staff is not None:
        title_parts.append(staff.name)
    title = " – ".join(title_parts)
    return CalendarEventPayload(
        title=title,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
    )


def sync_calendar_event_in_worker(
    db: Session,
    *,
    event_id: int,
    calendar_provider: CalendarProvider | None = None,
) -> None:
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()

    if event is None or event.status not in (
        CalendarSyncStatus.PENDING,
        CalendarSyncStatus.FAILED,
    ):
        return

    calendar_provider = calendar_provider or get_calendar_provider()

    booking = db.query(Booking).filter(Booking.id == event.booking_id).one()

    # Cross-check tenant to guard against a tampered job payload.
    if booking.tenant_id != event.tenant_id:
        return

    service = db.query(Service).filter(Service.id == booking.service_id).one()
    staff = (
        db.query(Staff).filter(Staff.id == booking.staff_id).one()
        if booking.staff_id is not None
        else None
    )

    payload = _build_event_payload(booking, service, staff)
    result = calendar_provider.create_event(payload)

    event.attempts += 1

    if result.success:
        event.status = CalendarSyncStatus.SYNCED
        event.provider_event_id = result.provider_event_id
        event.synced_at = datetime.now(timezone.utc)
        db.commit()
        return

    event.last_error = (result.error or "")[:500]
    if event.attempts >= settings.worker_max_retries:
        event.status = CalendarSyncStatus.FAILED
        db.commit()
        return
    db.commit()
    raise CalendarSyncError(result.error)


def get_calendar_event_for_booking(
    db: Session, booking_id: int, tenant_id: int
) -> CalendarEvent | None:
    return (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.booking_id == booking_id,
            CalendarEvent.tenant_id == tenant_id,
        )
        .first()
    )


def cancel_calendar_event_in_worker(
    db: Session,
    *,
    event_id: int,
    calendar_provider: CalendarProvider | None = None,
) -> None:
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()

    if event is None or event.status in (
        CalendarSyncStatus.CANCELLED,
        CalendarSyncStatus.CANCEL_FAILED,
    ):
        return

    booking = db.query(Booking).filter(Booking.id == event.booking_id).one()

    if booking.tenant_id != event.tenant_id:
        return

    # Events that were never synced to a provider need no provider call.
    if event.status in (CalendarSyncStatus.PENDING, CalendarSyncStatus.FAILED):
        event.status = CalendarSyncStatus.CANCELLED
        db.commit()
        return

    calendar_provider = calendar_provider or get_calendar_provider()
    result = calendar_provider.cancel_event(event.provider_event_id)

    event.cancel_attempts += 1

    if result.success:
        event.status = CalendarSyncStatus.CANCELLED
        db.commit()
        return

    event.last_error = (result.error or "")[:500]
    if event.cancel_attempts >= settings.worker_max_retries:
        event.status = CalendarSyncStatus.CANCEL_FAILED
        db.commit()
        return
    db.commit()
    raise CalendarCancelError(result.error)
