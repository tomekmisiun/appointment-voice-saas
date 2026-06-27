# MVP Demo Flow — Appointment Voice SaaS

Local simulated call-to-booking-to-notification-to-calendar scenario.

No real Twilio, SMS provider, or Google Calendar account is required.
All providers are faked locally.

## Prerequisites

1. Docker Compose stack running: `docker compose up -d`
2. Migrations applied: `make migrate`
3. Demo seed data loaded: `make seed-demo`

## Demo Actors

| Actor | Description |
|-------|-------------|
| Demo Business | "Quick Cuts Barber" — single-staff barber shop |
| Demo Staff | "Marek" — one active staff member |
| Demo Services | "Haircut" (30 min), "Beard Trim" (15 min) |
| Demo Hours | Monday–Saturday 09:00–18:00, Europe/Warsaw timezone |
| Demo Customer | Caller with phone +48600000001 |

## Step 1 — Simulate Incoming Call

The IVR simulation endpoint accepts a caller phone number and business ID and
starts a `VoiceSession`.

```
POST /api/v1/ivr/simulate/call
{
  "business_id": "<demo-business-id>",
  "caller_phone": "+48600000001"
}
```

**Expected result:**
- New `VoiceSession` row created with status `greeting`.
- Response includes `session_id` and greeting prompt text.
- Log shows: caller phone masked (e.g., `+486000****01`).

## Step 2 — Select Service (Keypad 1 = Haircut)

```
POST /api/v1/ivr/simulate/press
{
  "session_id": "<session-id>",
  "key": "1"
}
```

**Expected result:**
- `VoiceSession.selected_service_id` set to Haircut service.
- Response returns available slots for the next business day.
- Slots are in Europe/Warsaw local time (09:00, 09:30, 10:00, …).

## Step 3 — Select Slot (Keypad 1 = First Available)

```
POST /api/v1/ivr/simulate/press
{
  "session_id": "<session-id>",
  "key": "1"
}
```

**Expected result:**
- `VoiceSession.selected_slot` set to the chosen start time.
- Response asks for confirmation: "Press 1 to confirm."

## Step 4 — Confirm Booking (Keypad 1)

```
POST /api/v1/ivr/simulate/press
{
  "session_id": "<session-id>",
  "key": "1"
}
```

**Expected result:**
- `Booking` row created with status `confirmed`.
- `Customer` row created or matched by normalized phone.
- `VoiceSession.booking_id` set; session status = `completed`.
- `SMSMessage` rows queued in outbox:
  - Customer confirmation: "Your Haircut appointment at 09:00 is confirmed."
  - Business notification: "New booking: Haircut at 09:00 for +486000****01."
- `CalendarEvent` row created with status `pending_sync`.
- Response returns: "Your appointment is confirmed. Goodbye."

## Step 5 — Run Notification Worker

```
python -m app.worker --once
```

**Expected result:**
- `SMSMessage` rows transition from `pending` → `sent` using `FakeSMSProvider`.
- `FakeSMSProvider` records both messages in-memory or local log.
- `CalendarEvent` row transitions from `pending_sync` → `synced` using
  `FakeCalendarProvider`.
- `FakeCalendarProvider` records the event locally.
- No real SMS or calendar network call is made.

## Step 6 — Verify Records

```
GET /api/v1/bookings/<booking-id>
```

**Expected result:**
- Booking shows: status=confirmed, service=Haircut, staff=Marek, correct slot.

```
GET /api/v1/sms-messages?booking_id=<booking-id>
```

**Expected result:**
- Two messages with status=sent.

```
GET /api/v1/calendar-events?booking_id=<booking-id>
```

**Expected result:**
- One calendar event with status=synced, fake_event_id set.

## Step 7 — Cancel Booking

```
POST /api/v1/bookings/<booking-id>/cancel
{
  "reason": "Customer request"
}
```

**Expected result:**
- Booking status transitions to `cancelled`.
- `SMSMessage` rows queued for cancellation:
  - Customer: "Your Haircut appointment has been cancelled."
  - Business: "Booking cancelled: Haircut at 09:00."
- `CalendarEvent` queued for cancellation update.

## Step 8 — Run Worker Again

```
python -m app.worker --once
```

**Expected result:**
- Cancellation SMS messages sent through `FakeSMSProvider`.
- `CalendarEvent` updated to `cancelled` status in `FakeCalendarProvider`.

## Verifying the Full Flow as a Smoke Test

`AVS-G010` / `AVS-J003` will implement a single automated test that exercises
steps 1–8 end-to-end:

```
pytest tests/smoke/test_ivr_booking_flow.py -v
```

**Expected:** All assertions pass. No external network calls. Deterministic.

## No-Slot Path

If all slots are taken for the day, the IVR returns:

> "There are no available appointments for the selected service today.
>  Please try calling again tomorrow. Goodbye."

- No `Booking` is created.
- `VoiceSession` status = `no_slots`.

## Transfer Branch

If the caller presses 2 at the main menu, the system emits a transfer intent.
The simulation returns:

> "Transfer requested. Connecting to staff."

Call transfer is implemented (EPIC I). Twilio live-call transfer requires a
real phone number and is not exercisable in the local IVR simulator.

## Demo Assumptions

- Business timezone is Europe/Warsaw.
- Demo seed creates working hours for Monday–Saturday.
- Demonstration date must fall on a working day with at least one available
  slot; adjust the demo date in the seed if needed.
- No real phone numbers, Twilio accounts, or SMS provider credentials are
  required for the local demo.
