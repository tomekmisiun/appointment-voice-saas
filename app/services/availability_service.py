"""Availability slot generation.

Three schedule-related tables are consulted, in this fixed precedence
order (ADR 0003):

1. `WorkingHours` -- recurring weekly open windows, intersected between a
   staff member's own hours and the business's wide ones (P3-002).
2. `AvailabilityException` -- a one-off date override that fully replaces
   step 1's windows for that exact date (full closure, special hours, or
   no change), and always wins over step 3 if it's a closure (P3-003).
3. `RecurringStaffBlock` -- a recurring weekly unavailable window,
   subtracted from whatever step 1/2 left in place (P3-005). Unlike step
   2, this never goes stale when working hours change later, because it
   clips the then-current schedule at query time rather than a frozen
   snapshot of it -- see `docs/adr/0003-recurring-staff-blocks.md` for why
   that distinction required a separate model instead of reusing
   `AvailabilityException`.
"""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.domain_errors import NotFoundError
from app.models.availability_exception import AvailabilityException
from app.models.booking import Booking, BookingStatus
from app.models.recurring_staff_block import RecurringStaffBlock
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


def _intersect_time_windows(
    staff_windows: list[tuple[time, time]], salon_windows: list[tuple[time, time]]
) -> list[tuple[time, time]]:
    """Pairwise-intersect every staff window against every salon window,
    keeping only the non-empty overlaps (P3-002). Either side may hold more
    than one window (e.g. a split shift), so this is a full cross product,
    not a 1:1 zip."""
    overlaps = []
    for staff_start, staff_end in staff_windows:
        for salon_start, salon_end in salon_windows:
            start = max(staff_start, salon_start)
            end = min(staff_end, salon_end)
            if start < end:
                overlaps.append((start, end))
    return overlaps


def _subtract_time_windows(
    base_windows: list[tuple[time, time]], block_windows: list[tuple[time, time]]
) -> list[tuple[time, time]]:
    """Subtract every block window from every base window (P3-005),
    splitting a base window into 0, 1, or 2 remaining sub-windows per
    overlapping block. Blocks are applied one at a time so multiple blocks
    (e.g. a lunch break and a separate afternoon break) each carve their
    own gap out of whatever windows remain after the previous one."""
    result = list(base_windows)
    for block_start, block_end in block_windows:
        next_result = []
        for win_start, win_end in result:
            if block_end <= win_start or block_start >= win_end:
                next_result.append((win_start, win_end))
                continue
            if win_start < block_start:
                next_result.append((win_start, block_start))
            if block_end < win_end:
                next_result.append((block_end, win_end))
        result = next_result
    return result


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

    def _wh_windows(filter_staff_id: int | None) -> list[tuple[time, time]]:
        query = db.query(WorkingHours).filter(
            WorkingHours.business_id == business_id,
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week,
        )
        if filter_staff_id is not None:
            query = query.filter(WorkingHours.staff_id == filter_staff_id)
        else:
            query = query.filter(WorkingHours.staff_id.is_(None))
        return [(wh.start_time, wh.end_time) for wh in query.all()]

    def _has_any_schedule(filter_staff_id: int | None) -> bool:
        """Whether any WorkingHours row exists for this scope, on *any*
        day -- not just query_date's weekday. Distinguishes "never
        configured a schedule" (use the other side's hours as-is, even if
        that's empty today) from "has a schedule but not for this specific
        day" (closed today, not a fallback to the other side)."""
        query = db.query(WorkingHours.id).filter(
            WorkingHours.business_id == business_id,
            WorkingHours.tenant_id == tenant_id,
        )
        if filter_staff_id is not None:
            query = query.filter(WorkingHours.staff_id == filter_staff_id)
        else:
            query = query.filter(WorkingHours.staff_id.is_(None))
        return query.first() is not None

    salon_windows = _wh_windows(None)

    if staff_id is None:
        working_hours = salon_windows
    else:
        staff_windows = _wh_windows(staff_id)

        if not _has_any_schedule(staff_id):
            # This staff member never configured their own hours -- follow
            # the salon's hours as-is, today and every day (P3-002).
            working_hours = salon_windows
        elif not _has_any_schedule(None):
            # The business never configured business-wide hours at all --
            # nothing to intersect against; use the staff's own hours for
            # today unmodified (preserves pre-P3-002 behavior for
            # businesses that only ever configure per-staff hours).
            working_hours = staff_windows
        else:
            # Both sides have a managed schedule (on at least one day
            # each): a slot only counts if both are open *today*
            # specifically (P3-002 acceptance). If either side has no row
            # for today, the cross product is naturally empty -- closed,
            # not a fallback to the other side.
            working_hours = _intersect_time_windows(staff_windows, salon_windows)

    if not working_hours:
        return []

    # P3-003: business-wide (staff_id IS NULL) and staff-specific exceptions
    # for this date are merged into one set here, then handled uniformly --
    # a business-wide closure always wins (the `any(is_closed)` check below
    # doesn't distinguish scope), and business-wide special hours apply to
    # a staff-specific search exactly like the staff's own would. This is
    # an OR/union of whichever rows exist, not an intersection: unlike
    # P3-002's WorkingHours handling, a staff-specific exception doesn't
    # get clipped to a business-wide one, since exceptions already mean
    # "this date is different from the rule" rather than "this is the
    # rule" -- deliberately unchanged from pre-P3-002/003 behavior.
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

    effective_windows = (
        [(exc.start_time, exc.end_time) for exc in special_hours]
        if special_hours
        else working_hours
    )

    # P3-005 (ADR 0003): recurring blocks subtract from whatever windows
    # AvailabilityException left in place, rather than replacing them like
    # a one-off exception does -- this runs *after* exceptions so a block
    # always clips the current schedule, never a frozen snapshot of it (see
    # the ADR for why this had to be a separate model from
    # AvailabilityException). A business-wide closure already returned []
    # above, so blocks are only reached when the day is genuinely open.
    block_query = db.query(RecurringStaffBlock).filter(
        RecurringStaffBlock.business_id == business_id,
        RecurringStaffBlock.tenant_id == tenant_id,
        RecurringStaffBlock.day_of_week == day_of_week,
    )
    if staff_id is not None:
        block_query = block_query.filter(
            or_(
                RecurringStaffBlock.staff_id == staff_id,
                RecurringStaffBlock.staff_id.is_(None),
            )
        )
    else:
        block_query = block_query.filter(RecurringStaffBlock.staff_id.is_(None))
    block_windows = [(b.start_time, b.end_time) for b in block_query.all()]
    if block_windows:
        effective_windows = _subtract_time_windows(effective_windows, block_windows)

    candidate_starts: list[datetime] = []
    for window_start, window_end in effective_windows:
        candidate_starts.extend(
            _slots_in_window(query_date, window_start, window_end, duration_minutes, tz)
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
