from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.availability_exception import AvailabilityException
from app.models.booking import Booking, BookingStatus
from app.models.working_hours import WorkingHours
from app.services.business_service import require_business
from app.services.service_service import require_service
from app.services.staff_service import require_staff


def _slots_in_window(
    query_date: date,
    window_start: time,
    window_end: time,
    duration_minutes: int,
    tz: ZoneInfo,
) -> list[datetime]:
    """Return UTC slot starts that fit entirely within the local time window."""
    duration = timedelta(minutes=duration_minutes)
    start_local = datetime.combine(query_date, window_start).replace(tzinfo=tz)
    end_local = datetime.combine(query_date, window_end).replace(tzinfo=tz)
    slots: list[datetime] = []
    current = start_local
    while current + duration <= end_local:
        slots.append(current.astimezone(timezone.utc))
        current += duration
    return slots


def get_available_slots(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    service_id: int,
    staff_id: int | None,
    query_date: date,
) -> list[tuple[datetime, datetime]]:
    """Return (starts_at, ends_at) UTC pairs available for booking on query_date."""
    business = require_business(db, business_id, tenant_id)
    svc = require_service(db, service_id, tenant_id)
    if svc.business_id != business_id:
        raise NotFoundError("Service not found")
    if staff_id is not None:
        staff = require_staff(db, staff_id, tenant_id)
        if staff.business_id != business_id:
            raise NotFoundError("Staff member not found")
    return _get_available_slots_for_duration(
        db,
        business=business,
        business_id=business_id,
        tenant_id=tenant_id,
        staff_id=staff_id,
        duration_minutes=svc.duration_minutes,
        query_date=query_date,
    )


def get_available_slots_for_total_duration(
    db: Session,
    *,
    tenant_id: int,
    business_id: int,
    total_duration_minutes: int,
    staff_id: int | None,
    query_date: date,
) -> list[tuple[datetime, datetime]]:
    """Like get_available_slots(), but for a combined duration across
    multiple services (P2-008/P2-009) rather than a single service_id's
    duration_minutes. Used to search availability for a multi-service
    appointment built from BookingLineItem rows."""
    business = require_business(db, business_id, tenant_id)
    if staff_id is not None:
        staff = require_staff(db, staff_id, tenant_id)
        if staff.business_id != business_id:
            raise NotFoundError("Staff member not found")
    return _get_available_slots_for_duration(
        db,
        business=business,
        business_id=business_id,
        tenant_id=tenant_id,
        staff_id=staff_id,
        duration_minutes=total_duration_minutes,
        query_date=query_date,
    )


def _get_available_slots_for_duration(
    db: Session,
    *,
    business,
    business_id: int,
    tenant_id: int,
    staff_id: int | None,
    duration_minutes: int,
    query_date: date,
) -> list[tuple[datetime, datetime]]:
    tz = ZoneInfo(business.timezone)
    day_of_week = query_date.weekday()  # 0=Monday, 6=Sunday

    wh_query = db.query(WorkingHours).filter(
        WorkingHours.business_id == business_id,
        WorkingHours.tenant_id == tenant_id,
        WorkingHours.day_of_week == day_of_week,
    )
    if staff_id is not None:
        wh_query = wh_query.filter(WorkingHours.staff_id == staff_id)
    else:
        wh_query = wh_query.filter(WorkingHours.staff_id.is_(None))
    working_hours = wh_query.all()

    if not working_hours:
        return []

    exc_query = db.query(AvailabilityException).filter(
        AvailabilityException.business_id == business_id,
        AvailabilityException.tenant_id == tenant_id,
        AvailabilityException.date == query_date,
    )
    if staff_id is not None:
        exc_query = exc_query.filter(
            or_(
                AvailabilityException.staff_id == staff_id,
                AvailabilityException.staff_id.is_(None),
            )
        )
    else:
        exc_query = exc_query.filter(AvailabilityException.staff_id.is_(None))
    exceptions = exc_query.all()

    if any(e.is_closed for e in exceptions):
        return []

    special_hours = [
        e for e in exceptions if not e.is_closed and e.start_time and e.end_time
    ]

    candidate_starts: list[datetime] = []
    if special_hours:
        for exc in special_hours:
            candidate_starts.extend(
                _slots_in_window(
                    query_date, exc.start_time, exc.end_time, duration_minutes, tz
                )
            )
    else:
        for wh in working_hours:
            candidate_starts.extend(
                _slots_in_window(
                    query_date, wh.start_time, wh.end_time, duration_minutes, tz
                )
            )

    candidate_starts = sorted(set(candidate_starts))
    if not candidate_starts:
        return []

    next_day = query_date + timedelta(days=1)
    day_start_utc = datetime.combine(query_date, time(0, 0)).replace(tzinfo=tz).astimezone(timezone.utc)
    day_end_utc = datetime.combine(next_day, time(0, 0)).replace(tzinfo=tz).astimezone(timezone.utc)

    booking_query = db.query(Booking).filter(
        Booking.business_id == business_id,
        Booking.tenant_id == tenant_id,
        Booking.status == BookingStatus.CONFIRMED,
        Booking.starts_at < day_end_utc,
        Booking.ends_at > day_start_utc,
    )
    if staff_id is not None:
        booking_query = booking_query.filter(Booking.staff_id == staff_id)
    bookings = booking_query.all()

    duration = timedelta(minutes=duration_minutes)
    now_utc = datetime.now(tz=timezone.utc)

    free: list[tuple[datetime, datetime]] = []
    for slot_start in candidate_starts:
        if slot_start <= now_utc:
            continue
        slot_end = slot_start + duration
        blocked = any(
            b.starts_at < slot_end and b.ends_at > slot_start for b in bookings
        )
        if not blocked:
            free.append((slot_start, slot_end))

    return free
