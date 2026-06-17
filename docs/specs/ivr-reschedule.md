# IVR reschedule (P1-003)

## Objective

Let a caller reschedule or cancel their existing booking via the same IVR
call flow, without staff intervention.

## Problem / user story

A customer who already booked an appointment calls back wanting a different
time, or wants to cancel. Today the IVR can only create new bookings or
transfer to staff — there is no self-service path for an existing booking.

## Requirements

1. At the main menu, a caller can press a new digit ("3") to manage an
   existing appointment.
2. The caller is identified by their caller ID phone number (same
   normalize-and-match approach already used for SMS replies in P1-002), no
   PIN or booking reference needed.
3. The system looks up that caller's soonest upcoming `CONFIRMED` booking for
   the business. If none exists, the caller is told so and returned to the
   main menu without being charged an invalid-key strike.
4. If a booking is found, the caller can: cancel it, reschedule it to a new
   slot, or go back to the main menu.
5. Reschedule keeps the same service (and staff, if any) as the original
   booking — only the time changes. The caller picks a new slot from the
   same availability search used for new bookings.
6. Reschedule is implemented as cancel-the-old-booking +
   create-a-new-booking, reusing `cancel_booking()`/`create_booking()` as-is
   so audit logging, SMS notifications, and calendar sync all keep working
   unchanged. This means the caller gets both a cancellation SMS and a new
   confirmation SMS — accepted as a minor UX tradeoff for reusing tested,
   audited primitives instead of adding in-place booking mutation.
7. Cancelling or completing a reschedule must not break the no-input /
   invalid-key counters or the `*` repeat key already implemented for every
   other interactive step (P1-005/P1-006/P1-007).

## Non-goals

- Changing service or staff during a reschedule (out of scope; would need a
  full service/slot re-selection flow).
- Picking which booking to manage when a caller has more than one upcoming
  booking (out of scope; soonest-upcoming is the existing precedent from
  P1-002's SMS reply handling).
- PIN/identity verification beyond caller ID matching.

## Acceptance criteria

- Pressing "3" at the main menu with no matching booking returns to the main
  menu with an explanatory prompt, `invalid_key_count` unchanged.
- Pressing "3" with a matching booking presents cancel/reschedule/back
  options.
- Cancel ends the call with the booking's status set to `CANCELLED`.
- Reschedule presents available slots for the same service; picking one
  cancels the old booking, creates a new one at the new time, and ends the
  call with a confirmation message.
- `*` and no-input behave the same way on the two new steps as on every
  existing step.

## Impacted files

- `alembic/versions/` — new migration adding `voice_sessions.managed_booking_id`.
- `app/models/voice_session.py` — new column, new `IvrStep.BOOKING_CANCELLED`.
- `app/services/booking_service.py` — extract shared
  `get_next_confirmed_booking()` (currently duplicated as a private helper
  in `sms_reply_service.py`).
- `app/services/sms_reply_service.py` — use the shared helper.
- `app/services/ivr_service.py` — new steps, main menu option, terminal-step
  list, repeat/no-input reprompt branches.
- `tests/test_avs_p1003_ivr_reschedule.py` (new), full suite re-run for
  regressions.

## Risks

- Tenant isolation: booking lookup must filter by `business_id` +
  `tenant_id`, matching every other query in this file.
- Double-booking: `create_booking()` already re-checks the exclusion
  constraint, so a slot taken between search and confirm is rejected the
  same way it is for new bookings today.

## Verification plan

- `pytest tests/test_avs_p1003_ivr_reschedule.py -v`
- Full suite in Docker: `pytest -n 2 --cov=app --cov-fail-under=85`
- `ruff check`
