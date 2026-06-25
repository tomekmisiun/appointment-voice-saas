# ADR 0006: Two-Way Calendar Sync

- **Status:** Accepted
- **Date:** June 2026
- **Roadmap:** P3-014 (ADR only — explicitly rejects implementation; no code
  changes accompany this decision)
- **Amended by:** ADR 0008. Decision 1's prohibition on availability-blocking
  busy periods is superseded. External mutation of local bookings and full
  bidirectional conflict resolution remain rejected.

## Context

`docs/audits/pre-p3-readiness-audit.md` §9 flags P3-014 as **High** risk:
*"any 'yes' answer here would contradict the existing accepted architecture
and needs to be argued explicitly, not just documented"* — and scopes the
default recommendation as *"reject full two-way sync in favor of one-way
import + conflict alerts."* This ADR makes that call explicitly, rather than
leaving it implied by ADR 0002 alone.

The relevant existing state:

- **ADR 0002 §1** already decided: *"PostgreSQL is the booking source of
  truth... External calendars... are integration views. They must never
  decide whether a booking can be created, cancelled, or modified."* Every
  calendar interaction shipped so far (`CalendarProvider.create_event()`/
  `update_event()`/`cancel_event()`) is outbound-only, exactly matching this
  rule — nothing in this product today reads from, or reacts to changes in,
  an external calendar.
- **ADR 0005** (the P3-011 spike, merged immediately before this ADR)
  sketched a *read-only* `get_busy_periods()` addition to `CalendarProvider`,
  but deliberately deferred the question this ADR exists to answer: ADR 0005
  §2 states an imported `BusyPeriod` "must never become a fourth
  availability-subtraction step" and that *"P3-014 (not this spike) is
  scoped to decide [whether two-way sync happens at all] deliberately."*
  This ADR is that deliberate decision.
- The roadmap's named risk for this item is explicit: *"Calendar becomes
  competing source of truth."* Concretely, "two-way sync" could mean several
  different things of escalating risk: (a) reading busy/free for an
  informational alert (ADR 0005, already decided, read-only, no write-back);
  (b) treating an external event as blocking, i.e. an imported `BusyPeriod`
  removes a slot from availability search; (c) treating an external
  edit/deletion of a *synced* event (one this product itself created via
  `create_event()`) as authoritative — e.g. a staff member deleting the
  Google Calendar event directly cancels the underlying `Booking`; (d) full
  bidirectional reconciliation with conflict resolution for simultaneous
  edits on both sides. This ADR addresses (b), (c), and (d) — (a) is already
  settled by ADR 0005 and is not reopened here.

## Decision

**Reject (b), (c), and (d). Reaffirm ADR 0002 §1 without amendment: a
`Booking`'s status, time, and existence are decided exclusively by this
product's own service layer (`app/services/booking_service.py`), never by
reading or reacting to the state of an external calendar.** Concretely:

1. **No availability-blocking from imported busy/free data (rejects (b)).**
   This is ADR 0005 §2's rule, reaffirmed here as this ADR's own holding, not
   just inherited: `_get_available_slots_for_duration()`'s precedence chain
   (`WorkingHours` → `AvailabilityException` → `RecurringStaffBlock`) stays
   exactly three steps. An imported `BusyPeriod` (if ADR 0005's sketch is
   ever implemented) feeds only the informational conflict-alert path ADR
   0005 §2 describes — never a fourth subtraction step.

2. **No reactive sync from synced-event mutation (rejects (c)).** If a staff
   member edits or deletes the Google Calendar event that
   `sync_calendar_event_in_worker()` created for one of their bookings, that
   mutation is never read back. The `Booking` row is unaffected; the next
   outbound sync attempt (e.g. a reschedule) will either succeed (recreating
   the appropriate event) or fail and be retried/reconciled by the existing
   `CalendarEvent.status`/`reconciliation_service.py` machinery — the same
   failure handling that already exists for any other sync failure, not a
   new "the external calendar disagrees with us" code path. A booking can
   only be cancelled or rescheduled through this product's own API
   (`cancel_booking()`/`reschedule_booking()`, including the admin-override
   path), full stop.

3. **No bidirectional conflict resolution (rejects (d)).** Because (b) and
   (c) are both rejected, there is no scenario in this product where two
   sides can each "win" a simultaneous edit — there is only one side that
   ever writes booking state. This is what keeps the roadmap's named risk
   ("Calendar becomes competing source of truth") from ever materializing,
   rather than requiring a conflict-resolution policy to manage it after the
   fact.

This ADR does not change, and does not need to change, a single line of
existing code — `CalendarProvider`'s outbound-only shape, ADR 0002 §1, and
ADR 0005's read-only sketch are all already consistent with this decision.
What this ADR adds is the explicit, citable record that this was a
deliberate choice for the harder cases ((b)/(c)/(d)), not just an
accident of nothing having been built yet.

## Alternatives considered

1. **Treat a synced event's external deletion/edit as authoritative** (case
   (c) above — e.g. poll or use push notifications to detect a staff member
   deleted their synced Google Calendar event, then auto-cancel the
   `Booking`). Rejected: this is exactly "external calendar decides whether
   a booking can be cancelled," the literal thing ADR 0002 §1 prohibits: it
   would also require distinguishing "staff deleted it on purpose" from "the
   calendar app had a sync glitch" or "staff is reorganizing their calendar
   view," with no reliable signal to tell those apart, and a wrong guess
   silently cancels a real paying customer's appointment with no recourse.
2. **Full bidirectional reconciliation with a conflict-resolution policy**
   (case (d) — e.g. last-write-wins by timestamp, or a manual-review queue
   for conflicts). Rejected: this is the highest-complexity option for a
   risk the roadmap's own acceptance criteria says to avoid entirely
   ("ADR rejects or scopes two-way sync safely") rather than manage;
   building conflict-resolution machinery is solving a problem this ADR's
   §1–3 decisions make structurally impossible to encounter in the first
   place.
3. **Let imported busy/free data block availability (case (b)), but only
   for a feature-flagged subset of businesses.** Rejected: a feature flag
   narrows *who* hits the bug, not whether it is one — the underlying
   problem (external state silently deciding booking eligibility, with no
   guarantee the imported data is even accurate or current) is unchanged by
   gating its rollout.
4. **Reopen ADR 0002 §1 itself** (i.e. argue Postgres should no longer be
   sole source of truth). Rejected outright, not seriously entertained: no
   product requirement in this roadmap calls for it, and doing so would
   invalidate the double-booking guarantees `no_overlapping_staff_bookings`
   and `_check_double_booking()` already provide, which two prior incidents
   (PRs #42/#45) required real engineering effort to close — reopening the
   source-of-truth question would risk reintroducing that exact class of
   bug for no stated benefit.

## Consequences

**Positive:**
- The roadmap's named risk for this item ("Calendar becomes competing source
  of truth") cannot occur by construction, not by discipline — there is
  structurally only one writer of booking state.
- ADR 0002 §1 needs no amendment; every prior and future calendar-related
  decision (ADR 0005's sketch, P3-010's visibility work) can keep treating
  it as settled, unconditional law rather than a default that two-way sync
  might someday override.
- Staff using their personal Google Calendar for personal commitments don't
  need to worry that an accidental edit or deletion of a synced event
  silently cancels a customer's real appointment.

**Negative / follow-ups:**
- This explicitly does **not** serve a business that wants "true" two-way
  sync — e.g. a staff member blocking time by adding an event directly in
  Google Calendar and having it instantly reflected as unavailable in the
  booking engine. The existing, supported way to block a staff member's time
  in this product is to enter it directly here
  (`AvailabilityException`/`RecurringStaffBlock`), not via an external
  calendar. If that becomes a real, validated product requirement later, it
  requires a **new ADR that explicitly supersedes this one's §1–3**, with a
  conflict-resolution policy designed up front — not a reinterpretation of
  this ADR's scope.
- ADR 0005's informational conflict-alert delivery mechanism (the only
  sanctioned consequence of any future busy/free import) remains undesigned.
  This ADR does not design it either — it is implementation work for
  whichever task picks up ADR 0005's sketch, now that this ADR has confirmed
  there is no broader two-way-sync question still pending that would change
  its shape.
- P3-010 (private calendar visibility) is unaffected by this decision — its
  scope is the *outbound* sync direction (what this product writes to an
  external calendar), which this ADR does not touch.
