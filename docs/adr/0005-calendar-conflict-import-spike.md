# ADR 0005: Calendar Conflict Import Spike

- **Status:** Accepted
- **Date:** June 2026
- **Roadmap:** P3-011 (ADR/spike + interface sketch only — no implementation;
  feeds P3-014's two-way-sync ADR and informs, but does not block, P3-010's
  visibility work)
- **Amended by:** ADR 0008. Its section 2 prohibition on availability
  subtraction is superseded; privacy-minimal read-only busy import remains.

## Context

`docs/archive/audits/pre-p3-readiness-audit.md` §9 flags P3-011 explicitly: *"High
risk of scope creep into full two-way sync if not kept as a spike"* — and
scopes it as *"ADR/spike only, interface sketch, no implementation"*. This
ADR is that spike.

The relevant existing state:

- **ADR 0002 §1** already decided: *"PostgreSQL is the booking source of
  truth... External calendars... are integration views. They must never
  decide whether a booking can be created, cancelled, or modified."* All
  calendar sync today is **outbound only** — `CalendarProvider`
  (`app/services/calendar_provider.py`) exposes `create_event()`,
  `update_event()`, `cancel_event()`. There is no `import_events()` or
  `get_busy_periods()` method, and no code path ever reads from an external
  calendar.
- This means: if a staff member has a personal appointment, a doctor's visit,
  or any other commitment on their *actual* Google Calendar that was never
  entered into this product, the booking engine has no way to know about it.
  `WorkingHours`/`AvailabilityException`/`RecurringStaffBlock` only model
  time the salon itself configured — the roadmap's named risk for this item
  is exactly that: *"External conflicts missed."*
- `docs/archive/audits/pre-p3-readiness-audit.md` also separately scopes **P3-014**
  (two-way calendar sync ADR) as the place to decide *whether* to ever let
  external calendar state affect availability at all, with an explicit
  default recommendation to *"reject full two-way sync in favor of one-way
  import + conflict alerts."* P3-011 (this ADR) is scoped narrower and
  earlier: investigate what a one-way **read** of external busy/free data
  would even look like, as a contained spike, without pre-deciding P3-014's
  question.

## Decision

### 1. Scope: read-only busy/free import, never written back into availability by this spike

This spike investigates importing **busy/free periods only** from an
external calendar — never event titles, descriptions, attendees, or
locations. This mirrors the only data shape `app/core/calendar.py`'s
outbound side already commits to keeping minimal, and pre-empts most of
P3-010's privacy concern for the *inbound* direction before P3-010 even
starts (P3-010 itself is about the *outbound* side — whether a customer's
name/service shows up on a staff member's synced calendar event, not
anything inbound).

Sketch of the adapter contract extension (interface only — **no
implementation**, no real provider wiring, this spike does not touch
`app/services/calendar_provider.py`):

```python
@dataclass(frozen=True)
class BusyPeriod:
    starts_at: datetime
    ends_at: datetime
    external_ref: str | None  # provider's opaque event id, for dedup only

class CalendarProvider(Protocol):
    ...  # existing create_event/update_event/cancel_event, unchanged

    def get_busy_periods(
        self, calendar_id: str, *, window_start: datetime, window_end: datetime
    ) -> list[BusyPeriod]:
        ...
```

A real implementation would need real OAuth/credential handling per
`CalendarIntegration` row — that is provider-integration work, explicitly
**not** part of this spike, same as `create_event()` et al. were sketched in
ADR 0002 before EPIC H's real adapters existed.

### 2. Imported busy periods are surfaced as a conflict alert, never subtracted from availability

This is the central question the audit flagged scope-creep risk on, and this
ADR answers it directly: **an imported `BusyPeriod` must never participate
in `_get_available_slots_for_duration()`'s precedence chain
(`WorkingHours`/`AvailabilityException`/`RecurringStaffBlock`)** — it is not
a fourth subtraction step.

Treating an import as a fourth availability layer would mean external
calendar state *decides whether a booking can be created* — the exact thing
ADR 0002 §1 already ruled out, and exactly the "full two-way sync" framing
P3-014 is supposed to decide on its own terms, not inherit by accident from
this spike's interface sketch.

Instead, the only safe use of imported busy/free data this spike endorses is
**informational**: a periodic comparison (same maintenance-tick pattern as
`reconciliation_service.py`/P3-013) between imported `BusyPeriod` rows for a
staff member's integration and that staff member's existing
`CONFIRMED`/`PENDING_PAYMENT` bookings for the same window, surfacing an
overlap as an admin-facing alert (e.g. a new audit action or a dedicated
table, not designed here) — never altering the booking, never blocking
booking creation, never feeding back into the availability search. The
salon's own booking record stays authoritative; a human decides what to do
about a detected conflict.

### 3. Polling, not push, for this spike's contract

`get_busy_periods()` is sketched as a pull/poll method (caller supplies a
time window), not a webhook receiver. Push-based calendar change
notifications (e.g. Google Calendar push channels) require a publicly
reachable, domain-verified webhook endpoint and a channel-renewal lifecycle —
materially more integration surface than a spike should take on. If a real
implementation later needs push for latency reasons, that is a follow-up
decision for whoever implements the real adapter, not a blocker for this
ADR's contract sketch.

## Alternatives considered

1. **Treat imported busy periods as a fourth availability-subtraction step**
   (same pattern as `RecurringStaffBlock`). Rejected: this is, in substance,
   two-way sync — external calendar state would now decide booking
   eligibility, reopening exactly the question ADR 0002 §1 already closed
   and that P3-014 is specifically scoped to re-examine deliberately, not
   inherit as a side effect of an "import spike."
2. **Push-based (webhook) import instead of polling.** Rejected for this
   spike: materially higher integration complexity (domain verification,
   channel renewal) for no benefit the spike's stated goal (investigate
   feasibility, sketch a safe contract) needs. Not foreclosed for a real
   future implementation.
3. **Import full event details (title/description/attendees), not just
   busy/free.** Rejected: no product requirement needs more than busy/free
   to detect a conflict, and importing full details would create a new,
   broader privacy-sensitive data-handling surface (a staff member's
   personal calendar contents now stored in this product's database) with
   no offsetting benefit.
4. **Do nothing — leave external conflicts undetected.** Rejected: this is
   the status quo the roadmap's risk note (*"External conflicts missed"*)
   already flags as a real, named gap; a contained, alert-only spike closes
   it without the scope-creep risk of full sync.

## Consequences

**Positive:**
- A concrete, narrow contract (`get_busy_periods()` → `BusyPeriod`) exists
  for P3-014 to either adopt, amend, or reject when it makes the two-way-sync
  call — P3-014 is not starting from a blank page, but it is also not
  pre-committed to anything beyond a read-only sketch.
- The "informational alert, never authoritative" rule directly closes the
  scope-creep risk the audit named, while still addressing the underlying
  product risk (missed external conflicts) with a contained, additive
  surface.
- Busy/free-only import data is privacy-minimal by construction, consistent
  with whatever P3-010 decides for the *outbound* direction.

**Negative / follow-ups:**
- No alert-delivery mechanism (new model/audit action/notification surface
  for "external conflict detected") is designed here — this ADR only
  establishes that such a surface must be informational-only; its concrete
  shape is implementation work for whichever task picks this up after P3-014
  formalizes whether two-way sync (in any form) is wanted at all.
- A real `get_busy_periods()` implementation needs OAuth/credential storage
  per `CalendarIntegration` row, which does not exist yet (today's
  `CalendarIntegration.calendar_id` is enough for outbound writes but not
  for authenticating a read). Not designed here — provider-integration work,
  same boundary ADR 0002 drew around `create_event()` et al.
- This ADR does **not** decide whether P3-011's contract is ever actually
  implemented — P3-014 must make that call explicitly (see ADR 0002 §1's
  reaffirmation question), and a "yes" there is what would turn this spike's
  sketch into a real implementation task.
