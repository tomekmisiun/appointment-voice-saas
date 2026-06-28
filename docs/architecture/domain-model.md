# Domain Model

Domain vocabulary for **Appointment Voice SaaS**. All models below are
implemented in the repository. For the verified runtime state, see
`PROJECT_STATUS.md` and `docs/project/current-state.md`.

## Business

Tenant-scoped service provider that receives calls and owns scheduling data.
Examples: a barber shop, salon, or local repair business.

Key responsibilities:

- Stores public business identity, phone routing metadata, timezone, and
  notification preferences.
- Owns staff, services, working hours, availability exceptions, bookings, voice
  sessions, SMS messages, and calendar events.

## Staff

Person or bookable provider who can perform services for a business.

Key responsibilities:

- Belongs to a Business.
- Has working hours and availability exceptions.
- May be assigned to Bookings.
- May support only a subset of Services in later phases.

## Service

Bookable offering provided by a business.

Key responsibilities:

- Belongs to a Business.
- Defines customer-facing name, duration, active/inactive status, and optional
  price metadata.
- Drives availability slot length and booking selection.

## WorkingHours

Recurring weekly availability window for a business or staff member.

Key responsibilities:

- Defines day-of-week, local start time, local end time, and timezone context.
- Provides the baseline schedule used to generate available slots.
- Can be overridden by AvailabilityException.

## AvailabilityException

One-off override to normal working hours.

Key responsibilities:

- Blocks time for vacation, breaks, personal appointments, closures, or holidays.
- May optionally add special hours outside the normal schedule.
- Applies to a Business, Staff member, or both depending on the final model.

## Booking

Appointment reservation for a customer, service, staff member, and time slot.

Key responsibilities:

- Belongs to a Business and Customer.
- References selected Service and optionally Staff.
- Tracks start time, end time, status, source, confirmation state, cancellation
  reason, and reschedule lineage where needed.
- Must be protected against overlapping bookings for the same staff/resource.
- May originate from a VoiceSession.

## Customer

Person booking an appointment with a business.

Key responsibilities:

- Belongs to a Business.
- Stores phone number and optional name.
- Can have multiple Bookings.
- Must support deduplication by normalized phone number within a business.

## VoiceSession

Auditable record of an inbound call and its IVR state.

Key responsibilities:

- Belongs to a Business.
- Tracks caller phone number, provider call identifier, current state, selected
  service, selected slot, linked booking, and terminal outcome.
- Provides idempotency and recovery for provider retries or repeated keypad
  inputs.
- Can represent transfer intent when the caller requests staff transfer.

## NotificationOutbox

Outbox record for notification delivery (table `notification_outbox`; ORM
`app/models/notification_outbox.py`). Note: `app/core/sms.py::SmsMessage` is
a provider payload dataclass, not a persistent entity.

Key responsibilities:

- Belongs to a Business; optionally linked to a Booking.
- Tracks channel (currently SMS only), purpose, recipient phone, body, status,
  attempt count, provider message identifier, and last error.
- Purposes: booking confirmation, booking cancellation, booking reminder,
  external booking link, waitlist offer.
- Written before provider delivery is attempted (outbox pattern).

## CalendarEvent

External calendar representation of a Booking.

Key responsibilities:

- Belongs to a Business and usually maps to one Booking.
- Tracks provider, external event identifier, sync status, last synced time, and
  error details.
- Supports later Google Calendar or other calendar adapters.
- Represents an integration view of Booking; PostgreSQL Booking remains the
  source of truth.
