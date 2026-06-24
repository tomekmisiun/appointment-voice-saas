# ADR 0004: Deposits, Payment Holds, and Refunds

- **Status:** Accepted
- **Date:** June 2026
- **Roadmap:** P3-006 (decision only — Stripe implementation is P3-007,
  pending-payment booking state implementation is P3-008, both separate,
  later tasks)

## Context

`docs/audits/pre-p3-readiness-audit.md` §9 flags P3-006 as ADR-first,
blocking P3-007 ("Add Stripe payment links") and P3-008 ("Add
pending-payment booking state"): *"Architecture approved before payment
code."* The roadmap's risk note for this tier is explicit — *"Payments
corrupt booking lifecycle"* — so this decision has to be made before either
implementation task touches `Booking`.

The relevant existing state:

- **`Service.price_minor_units`/`currency`** (`app/models/service.py:27-28`)
  already exist — the full service price is already modeled. Nothing models
  a *deposit* (a partial, separately-configured amount) yet.
- **`BookingStatus`** (`app/models/booking.py:11-13`) has exactly two values:
  `CONFIRMED`, `CANCELLED`. There is no notion of a booking that exists but
  isn't yet confirmed.
- **The DB-level double-booking guard** is a Postgres exclusion constraint,
  not just an application check:
  ```sql
  ALTER TABLE bookings ADD CONSTRAINT no_overlapping_staff_bookings
  EXCLUDE USING gist (staff_id WITH =, tstzrange(starts_at, ends_at, '[)') WITH &&)
  WHERE (status = 'confirmed' AND staff_id IS NOT NULL)
  ```
  (`alembic/versions/2b3c4d5e6f7a_add_booking_no_overlap_constraint.py`).
  The application-level mirror, `_check_double_booking()`
  (`app/services/booking_service.py:31-56`), also filters on
  `Booking.status == BookingStatus.CONFIRMED` only. **Any new status added
  without touching both of these will not participate in double-booking
  protection at all** — this is the central fact this ADR has to resolve
  before P3-008 can safely add a new status.
- **`cancel_booking()`** (`app/services/booking_service.py:271-339`) always:
  sends a customer-facing "your appointment has been cancelled" SMS, fires
  calendar cancellation, and offers the freed slot to the next matching
  waitlist entry. A booking that was only ever a payment hold the customer
  never completed is not the same event as a real confirmed booking being
  cancelled — reusing this function unmodified for hold expiry would send a
  confusing "cancelled" message for an appointment the customer never had
  confirmed.
- **AVS-TD-031-style precedent:** this codebase already has one external
  payment surface planned (P4-007 Stripe **Billing** model, subscriptions).
  That is a different Stripe product (Billing/subscriptions) for a different
  purpose (charging the salon for *using this SaaS*) than this ADR's scope
  (charging the salon's *customer* a deposit for *a booking*). Naming below
  is chosen to avoid the two ever being confused in code search.

## Decision

### 1. Deposits are a separate, explicit per-service configuration — not derived from price

Add two nullable columns to `Service`:

```
deposit_required     Boolean, NOT NULL, default False
deposit_minor_units  Integer, NULLABLE   (set only when deposit_required=True)
```

A deposit is a **flat amount in the service's existing `currency`**, set
independently of `price_minor_units`. Rejected alternative: deriving the
deposit as a percentage of price — real businesses sometimes want a fixed
deposit regardless of price (e.g. a flat "no-show fee" amount), percentage
math introduces rounding/currency edge cases this ADR doesn't need to solve
yet, and a flat amount is trivially reusable as "the deposit *is* the price"
for a business that wants full prepayment (set
`deposit_minor_units == price_minor_units`). If per-business percentage
deposits become a real requirement later, that's a new ADR, not a
reinterpretation of this field.

### 2. A new `BookingPayment` model — not new columns on `Booking`

```
BookingPayment
  id
  tenant_id          FK tenants.id, NOT NULL
  business_id        FK businesses.id, NOT NULL
  booking_id         FK bookings.id, NOT NULL, UNIQUE (one payment per booking)
  provider           String, NOT NULL              (e.g. "stripe")
  provider_session_id String, NULLABLE             (Stripe Checkout Session / Payment Link id)
  provider_payment_id String, NULLABLE             (Stripe PaymentIntent id, set on success)
  amount_minor_units Integer, NOT NULL
  currency           String(3), NOT NULL
  status             String, NOT NULL  (pending | succeeded | failed | refunded)
  failure_reason     String, NULLABLE
  created_at         DateTime, server_default now()
  paid_at            DateTime, NULLABLE
  refunded_at        DateTime, NULLABLE
```

Named `BookingPayment`, not `Payment`, specifically so it cannot be confused
with the future P4-007 Stripe Billing/subscription model in a `grep` or a
casual reading of `app/models/` — they are unrelated payment surfaces
(customer-pays-for-a-booking vs. salon-pays-for-the-SaaS). This mirrors the
existing pattern of `NotificationOutbox`/`CalendarEvent`: a dedicated
side-effect-tracking table per external integration, not new columns bolted
onto `Booking` directly (`app/models/notification_outbox.py`,
`app/models/calendar_event.py` are the precedent).

### 3. A payment hold *does* reserve the slot — via a new `PENDING_PAYMENT` status, not a third "expired" status

```
BookingStatus.PENDING_PAYMENT = "pending_payment"
```

Added alongside `CONFIRMED`/`CANCELLED` (still only three values total — no
separate `EXPIRED`/`HOLD` status; see "Hold expiry" below for why expiry
reuses `CANCELLED`). When a service requires a deposit, P3-007's
payment-link creation flow creates the `Booking` row immediately, with
`status=PENDING_PAYMENT`, **before** the customer pays — not after. This is
the only way to actually prevent two customers from both reaching "pay now"
for the same slot.

This requires widening **all three** places that currently decide "is this
slot taken" to treat `PENDING_PAYMENT` as slot-reserving, equally with
`CONFIRMED` — not just the two double-booking guards named in Context:

- DB exclusion constraint: new migration changes the `WHERE` clause to
  `WHERE (status IN ('confirmed', 'pending_payment') AND staff_id IS NOT NULL)`.
- `_check_double_booking()` (`booking_service.py`): filter becomes
  `Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING_PAYMENT])`.
- **`availability_service.py`'s slot-generation query** (currently filters
  `Booking.status == BookingStatus.CONFIRMED` when deciding which candidate
  slots are already booked, around the function that builds free/busy from
  bookings for the day): same widening, or the availability search (and the
  IVR flow built on it) would keep showing a slot as free *after* a hold on
  it already exists, only to 409 the moment someone actually tries to book
  it via `_check_double_booking()` — the create-time guard would still be
  correct, but the search results lying about availability is its own bug.

All three edits are P3-008's job, not this ADR's, but are specified here
because getting any one of them wrong (e.g. widening the DB constraint and
the create-time check but missing the availability search, or vice versa)
either silently reopens the exact double-booking gap concurrent booking
attempts already required PR #45/AVS-TD-030 to close, or produces a
search-says-free / create-says-409 inconsistency — this ADR exists precisely
so neither mistake gets made independently by whoever implements P3-008.

**The hold-creation path must not reuse `create_booking()` unmodified.**
`create_booking()` (`app/services/booking_service.py:59-133`) today
hardcodes `status=BookingStatus.CONFIRMED` and unconditionally fires
`enqueue_booking_confirmation()` (customer "your appointment is confirmed"
SMS) and `enqueue_calendar_event()`/`enqueue_sync_calendar_event_job()` at
creation time, before the row is even committed as anything other than
confirmed. If P3-007 creates a payment hold by calling `create_booking()`
as-is, a customer who never completes payment will still receive a
confirmation SMS and get a calendar event synced for an appointment that
will be cancelled minutes later. P3-007/P3-008 must add a hold-creation path
(e.g. a `status` parameter on `create_booking()`, or a separate function
sharing its validation/double-booking-check logic) that, when creating a
`PENDING_PAYMENT` row, **skips** `enqueue_booking_confirmation()` and the
calendar-event enqueue entirely. Those side effects only fire once, at the
`PENDING_PAYMENT → CONFIRMED` transition in §5 below — not at hold creation,
and not duplicated at both points.

### 4. Hold expiry reuses `CANCELLED`, with a non-`CONFIRMED` source flag, not a new status or a notification

A `PENDING_PAYMENT` booking whose hold has expired (no successful payment
within `settings.booking_payment_hold_minutes`, a new setting — recommended
default 15) transitions to `BookingStatus.CANCELLED`, freeing the slot, via
a **new, dedicated function** (e.g. `expire_pending_payment_hold()`), not by
calling the existing `cancel_booking()` unmodified. It must still:

- Free the slot (same effect as `cancel_booking()`).
- Still attempt waitlist escalation for the now-free slot
  (`find_matching_waitlist_entries()`) — the slot being free is real, and a
  waiting customer should still hear about it.
- Log a **distinct** audit action (e.g. `AuditAction.BOOKING_HOLD_EXPIRED`,
  a new enum value — not `BOOKING_CANCELLED`), so "real" cancellations and
  abandoned-payment holds remain separately queryable.

But it must **not** send the customer a "your appointment has been
cancelled" SMS — the customer never had a confirmed appointment, only an
abandoned checkout session. `enqueue_booking_cancellation()` must not be
called from this path. (Whether to send a *different*, payment-specific
message — e.g. "your booking hold expired, please try again" — is a product
decision for P3-008, not this ADR; the only thing decided here is that the
existing cancellation-notification copy is wrong for this case.)

Reusing `CANCELLED` instead of adding a fourth status keeps `BookingStatus`
at three values and keeps every existing `status == CANCELLED` check
(reporting, listings) correct without changes — an expired hold genuinely
*is* "not happening," same as any other cancellation, just for a different
reason and via a different notification path.

### 5. Successful payment confirms the booking

On a successful Stripe webhook for a `BookingPayment`, set
`BookingPayment.status = succeeded`, `paid_at = now()`, and transition the
linked `Booking.status` from `PENDING_PAYMENT` to `CONFIRMED`. Use the
**existing** `AuditAction.BOOKING_CONFIRMED` (`app/models/audit_log.py:22`)
for this transition, rather than adding a new enum value — but note it is
not actually unused: `app/services/sms_reply_service.py:65-73` already logs
it when a customer confirms via SMS reply, with `source="sms_reply"`. Reuse
is fine *because* `AuditLog.source` already exists for exactly this kind of
disambiguation (the same way `BOOKING_CREATED`/`BOOKING_CANCELLED` already
distinguish `api`/`ivr`/an override reason via `source`) — the
payment-confirmation call site must pass a distinct value (e.g.
`source="stripe_webhook"`), not omit it or reuse `"sms_reply"`.

### 6. Refunds are recorded, not automated, by this ADR

Cancelling a `CONFIRMED` booking that has a `succeeded` `BookingPayment`
does **not** automatically call Stripe's refund API as part of this
decision. `cancel_booking()` gains no new behavior here. Refund *policy*
(full refund? partial, based on how close to the appointment the
cancellation happens? salon-configurable?) is a business-policy question
with no existing precedent in this codebase to anchor a default — inventing
one now would be designing product behavior inside an architecture
decision. What this ADR does fix: `BookingPayment.status = refunded` and
`refunded_at` exist as the place a refund (however and whenever triggered —
manual admin action initially, automatic policy later) gets recorded. P3-008
should implement at minimum a manual admin-triggered refund path; an
automatic refund policy is explicitly deferred to a future task/ADR if the
product actually needs one.

## Alternatives considered

1. **Add payment fields directly to `Booking`** (`deposit_status`,
   `stripe_payment_intent_id`, etc.). Rejected: conflates booking-lifecycle
   concerns with payment-integration concerns in one table, breaks the
   established one-model-per-concern pattern (`NotificationOutbox`,
   `CalendarEvent`), and would force every future payment-provider field
   onto the booking's own schema instead of an isolated, independently
   migratable table.
2. **Don't reserve the slot during payment (create the `Booking` only after
   payment succeeds).** Rejected: this reopens exactly the double-booking
   race this product has already paid down twice (tenant-isolation and
   waitlist-offer concurrency fixes, PRs #42/#45) — two customers could both
   start checkout for the same slot, and whichever pays first "wins" while
   the other's payment succeeds for a slot that's no longer available,
   producing a paid-but-unfulfillable booking. Reserving the slot via
   `PENDING_PAYMENT` with a short, enforced expiry is the standard pattern
   for this exact problem (the same approach Stripe Checkout itself uses for
   its own session expiry).
3. **A fourth `EXPIRED` status for abandoned holds**, distinct from
   `CANCELLED`. Rejected: every existing and future "is this booking
   actually happening" check (reporting, the bookings list filter, IVR/admin
   surfaces) would need to treat `EXPIRED` identically to `CANCELLED`
   everywhere it currently checks `status == CANCELLED`, for no behavioral
   benefit over the audit-log distinction this ADR already provides via
   `BOOKING_HOLD_EXPIRED`.
4. **Derive deposit amount as a percentage of `price_minor_units`** instead
   of a flat amount. Rejected: see Decision §1.
5. **Automate refund-on-cancellation now.** Rejected: see Decision §6 — no
   product requirement specifies a policy, and a wrong default (e.g.
   always-full-refund) is harder to walk back than deferring the decision.

## Consequences

**Positive:**
- The double-booking protection this product has twice had to retrofit
  under audit pressure (PRs #42, #45) is extended to the new status
  *before* any payment code exists, not discovered as a gap afterward.
- `BookingPayment` is independently testable and migratable, same benefit
  ADR 0003 noted for `RecurringStaffBlock` vs. bolting fields onto an
  existing table.
- A normal, no-deposit booking's existing notification/calendar/waitlist
  side effects are entirely unchanged by this ADR — `create_booking()`'s
  current behavior for a `CONFIRMED`-on-creation booking is untouched. Only
  the new `PENDING_PAYMENT` path is new, and §3 above fixes its contract
  (no confirmation SMS/calendar sync until the §5 confirm transition) so
  P3-007/P3-008 can't independently get this wrong.

**Negative / follow-ups:**
- Any code that currently treats "a `Booking` row exists" as "this slot is
  booked" (e.g. anything iterating `Booking` without a status filter) must
  be re-checked once `PENDING_PAYMENT` exists — it is a real, in-progress
  booking attempt, not yet a confirmed one. P3-008 must audit
  `list_bookings()`/IVR/admin-facing call sites for this.
- `BOOKING_HOLD_EXPIRED` is a new `AuditAction` enum value backed by a plain
  `String` column — adding it trips the `model-migration-pair` CI policy
  guard the same way P3-012's new audit actions did; needs a
  `scripts/ci/allow-no-migration` entry in the same commit (see existing
  entries for the exact phrasing).
- This ADR explicitly does **not** decide: the Stripe adapter shape (P3-007
  — should follow the existing `SmsProvider`/`CalendarProvider` adapter
  pattern), the hold-expiry worker job's exact wiring into
  `run_scheduled_maintenance()` (P3-008, same maintenance-tick pattern as
  P2-012/P3-013), or any refund *policy* (Decision §6).
- Implementation (model, migration, service wiring, API, worker job, tests)
  for both the `BookingPayment` model and the `PENDING_PAYMENT` status is
  tracked as **P3-008 (pending-payment state) before P3-007 (Stripe payment
  links)** — the reverse of `docs/audits/pre-p3-readiness-audit.md` §10's
  original ordering, per §3 above: P3-007's payment-link flow has no safe
  status to create a hold with until P3-008 lands. Not this task.
