# ADR 0008: External Busy Periods as Availability Exclusions

- **Status:** Accepted
- **Date:** 2026-06-24
- **Roadmap:** SAC-018 through SAC-024
- **Supersedes:** ADR 0005 section 2 and ADR 0006 decision 1 only

## Context

ADR 0002 correctly makes PostgreSQL bookings the source of truth and prohibits
external calendars from deciding whether a booking is created, modified, or
cancelled. ADRs 0005 and 0006 then went further: imported busy/free data was
limited to informational alerts and explicitly forbidden from removing offered
slots.

The validated staff-access requirement is narrower than two-way sync: an
employee's private external busy period should prevent the system from offering
that time for a new appointment. It must not create a booking, alter an existing
booking, or expose external event details. The current availability engine
already computes candidate slots from working hours and subtracts local blocks
and bookings (`app/services/availability_service.py`). A normalized read-only
busy period can be another exclusion without becoming a booking source of
truth.

## Decision

1. Local `Booking` rows remain the only source of truth for reservations.
   External changes can never create, reschedule, cancel, confirm, or otherwise
   mutate a booking.
2. Import only busy intervals for a bounded horizon. Do not persist titles,
   attendees, descriptions, locations, or customer data.
3. Fresh external busy intervals are subtractive inputs to availability after
   local working-hours, time-off/blocks, and local-booking rules.
4. External busy periods are a derived, expiring cache tied to one tenant,
   business, staff record, and integration. They are not domain calendar
   events and do not participate in booking history.
5. ICS and Google Calendar are read-only for the first versions. Existing
   outbound booking-event synchronization remains a separate adapter concern.
6. Provider failure or stale data changes integration health/freshness behavior
   according to an explicit pilot policy; it never changes existing bookings.
7. Disconnect revokes/erases credentials and invalidates imported busy periods.
8. Any future write-back or reaction to external event edits requires a new
   ADR; it is not permitted by this decision.

This supersedes only the “informational alert, never availability subtraction”
parts of ADRs 0005 and 0006. It does not supersede their rejection of external
booking authority or bidirectional conflict resolution, and it does not amend
ADR 0002's local-booking source-of-truth rule.

## Alternatives considered

### Keep external busy informational only

Rejected for the target product. It lets a salon advertise a slot that the
employee has already blocked in their personal calendar, defeating the primary
reason to connect that calendar.

### Import external events as local bookings

Rejected. It creates two booking authorities, leaks unnecessary event data,
and complicates cancellation, customer identity, notifications, and audit.

### Implement read/write Google synchronization immediately

Rejected. Write-back requires event identity, retry, idempotency, deletion,
conflict, consent, and source-of-truth policies beyond the read-only need.

### Query providers synchronously during availability requests

Rejected. Provider latency/outage would enter the booking critical path and
make deterministic availability impossible. Polling into normalized cached
periods fits existing worker/reconciliation patterns.

## Consequences

**Positive:** connected personal calendars prevent obvious scheduling
conflicts while local bookings remain authoritative; imports are privacy
minimal; provider calls stay outside availability requests.

**Negative:** stale-data and fail-open/fail-closed policy becomes a product
decision; polling introduces delay; ICS adds substantial SSRF risk; credentials
require encrypted storage and rotation.

**Required follow-ups:** implement secret storage, SSRF-safe fetching, normalized
busy periods, worker synchronization, freshness policy, timezone/DST tests, and
authorization hardening before enabling imports. No runtime change is made by
this ADR.

