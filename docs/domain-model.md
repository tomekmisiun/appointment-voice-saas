# Domain Model

Planned domain vocabulary for **Appointment Voice SaaS**. These are product
planning concepts, not database models implemented in the repository today.
Runtime implementation is not done yet unless verified by code and tests in
`PROJECT_STATUS.md`.

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

## SMSMessage

Notification intent and delivery record for SMS communication.

Key responsibilities:

- Belongs to a Business.
- Tracks recipient, purpose, provider, provider message identifier, status, and
  error details.
- Supports customer confirmations, business notifications, and later reminders.
- Should be written before provider delivery is attempted.
- Should represent booking, cancellation, and reschedule message intents before
  any real provider send attempt.

## CalendarEvent

External calendar representation of a Booking.

Key responsibilities:

- Belongs to a Business and usually maps to one Booking.
- Tracks provider, external event identifier, sync status, last synced time, and
  error details.
- Supports later Google Calendar or other calendar adapters.
- Represents an integration view of Booking; PostgreSQL Booking remains the
  source of truth.
