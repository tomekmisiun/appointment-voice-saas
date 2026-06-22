# ADR 0003: Recurring Staff/Business Blocks

- **Status:** Accepted
- **Date:** June 2026
- **Roadmap:** P3-005 (decision only — implementation is a separate, later task)

## Context

P3-004 ("Add staff time blocks") and P3-005 ("Add recurring staff blocks")
are adjacent roadmap items that both describe carving unavailable time out
of an otherwise-open schedule (e.g. a lunch break). `docs/audits/pre-p3-readiness-audit.md`
§9 flags a **high** conceptual overlap between them and requires this ADR
before any P3-005 code lands: *"must decide: extend `AvailabilityException`
with a recurrence rule, or add a new `RecurringBlock` model, before any code
lands."*

The existing schedule models, as implemented today:

- **`WorkingHours`** (`app/models/working_hours.py`): `day_of_week` +
  `start_time`/`end_time`, optionally scoped to a `staff_id` (nullable =
  business-wide). Pure "open" windows, recurring weekly. No notion of
  "closed" or "blocked."
- **`AvailabilityException`** (`app/models/availability_exception.py`): an
  **exact `date`**, optionally scoped to `staff_id`, with `is_closed: bool`.
  If `is_closed=True`, the whole day is closed. If `is_closed=False`, the
  row's `start_time`/`end_time` *replaces* the working-hours window for that
  date (`app/services/availability_service.py:120-141`) — it does not
  subtract a sub-interval from it.

This means P3-004's "one-off staff block" (e.g. "closed 12:00-13:00 today")
is not represented by a literal block field at all. It is built **indirectly**:
two `AvailabilityException` "special hours" rows for the same date — one for
the morning window, one for the afternoon window — whose combined effect is
a carved-out gap. This works for a *one-off* date because the rows are
computed once against that day's known working hours and never need to stay
in sync with anything.

That indirect trick does **not** generalize safely to a recurring block. A
recurring block must hold up against working hours that can change in the
future (new staff hours added, existing hours edited). If a recurring block
were encoded the same way — as recurring "replacement window" rows computed
against today's working hours — it would silently go stale the moment the
underlying working hours change, because the replacement windows were
computed as the complement of a specific, now-outdated working-hours range.
This is the crux of the decision this ADR resolves.

## Decision

**Add a new, dedicated `RecurringStaffBlock` model.** Do not extend
`AvailabilityException` with a recurrence rule.

```
RecurringStaffBlock
  id
  tenant_id        FK tenants.id, NOT NULL
  business_id      FK businesses.id, NOT NULL
  staff_id         FK staff.id, NULLABLE  (NULL = business-wide block)
  day_of_week      Integer, NOT NULL      (0=Monday .. 6=Sunday, same convention as WorkingHours)
  start_time       Time, NOT NULL
  end_time         Time, NOT NULL
  reason           String(255), NULLABLE
```

Indexes on `tenant_id`, `business_id`, `staff_id`, `day_of_week` (mirrors
`WorkingHours`' existing index set).

**Semantics — subtract, don't replace:** slot generation first computes
candidate open windows exactly as it does today (from `WorkingHours`, with
`AvailabilityException` closures/replacements applied as today). It then
**subtracts** any `RecurringStaffBlock` row matching that date's
`day_of_week` (and `staff_id`, or a business-wide block with `staff_id IS
NULL`) from the resulting candidate slots. Because the subtraction happens
against whatever candidates exist *at query time*, a recurring block never
goes stale when working hours change later — it always clips the
then-current schedule rather than a frozen snapshot of it.

**Precedence with `AvailabilityException`:** the two mechanisms stay
orthogonal and compose by always running in this order:

1. `AvailabilityException` decides which windows are open for the exact
   date (full closure, a replacement window, or unmodified working hours).
2. `RecurringStaffBlock` subtracts its recurring sub-interval from whatever
   came out of step 1.

A business-wide closure (`AvailabilityException.is_closed=True`) still
short-circuits to "no slots" before recurring blocks are even considered,
matching the existing precedence note for P3-003 ("business closure always
wins over staff availability").

**Why a new table instead of extending `AvailabilityException`:**

- Keeps each table's temporal axis singular and unambiguous:
  `WorkingHours`/`RecurringStaffBlock` are both "every week on weekday N";
  `AvailabilityException` is "this exact date." Mixing both axes into one
  table (`date: date | None` + `day_of_week: int | None` on the same row)
  would require every query against that table to branch on which axis is
  populated, and would make `is_closed`'s meaning ambiguous for a recurring
  row (a recurring full closure is already expressible today by simply not
  creating a `WorkingHours` row for that weekday).
- Avoids the stale-replacement-window correctness bug described above.
- Matches this codebase's existing pattern of one model per distinct
  schedule concept (`WorkingHours` for open windows, `AvailabilityException`
  for one-off date overrides) rather than collapsing concepts to minimize
  table count.

## Alternatives considered

1. **Extend `AvailabilityException` with a recurrence rule** (e.g. make
   `date` nullable, add nullable `day_of_week`). Rejected: conflates two
   temporal axes in one table, and the existing "replacement window"
   semantic produces the stale-window bug for anything recurring (see
   Context). Reusing the table would save one migration but at a real,
   ongoing correctness cost.
2. **Model blocks as negative `WorkingHours` rows** (e.g. a `is_block: bool`
   flag on `WorkingHours` itself). Rejected: `WorkingHours` rows are
   currently combined additively (a staff member can have multiple
   non-overlapping windows in a day); mixing in subtractive rows on the same
   table would require every existing `WorkingHours` query to filter by
   `is_block`, a wider blast radius than a new table.
3. **Do nothing — keep using the two-`AvailabilityException`-rows trick for
   recurring blocks too**, generated by a worker job that re-creates the
   rows whenever working hours change. Rejected: pushes a correctness
   problem into operational machinery (a worker job that must never miss a
   working-hours change) instead of solving it structurally; also produces
   N exception rows per recurrence per week with no natural end, an
   unbounded-growth and cleanup concern P3-005's roadmap scope ("Lunches/
   recurring unavailable windows") does not call for.

## Consequences

**Positive:**
- Recurring blocks are correct by construction against future working-hours
  changes — no synchronization job, no stale-row risk.
- `RecurringStaffBlock` is independently testable (subtraction logic) from
  `AvailabilityException` (window selection logic), keeping `tests/test_availability.py`-style
  coverage focused per concept.
- Symmetric with the existing `staff_id`-nullable convention used by
  `WorkingHours` and `AvailabilityException`, so this fork's contributors
  already know the pattern.

**Negative / follow-ups:**
- A third schedule-related table exists alongside `WorkingHours` and
  `AvailabilityException`. Anyone querying "is this business/staff
  available right now" must now consult three tables instead of two — this
  is an accepted complexity cost for correctness, but `availability_service.py`'s
  docstring should be updated when P3-005 is implemented to spell out the
  three-step precedence order from this ADR.
- **Explicitly out of scope for this ADR/initial P3-005 implementation:**
  date-range-bounded recurrence (e.g. "this lunch block only applies June
  through August"), and a mechanism to lift/override a recurring block for
  one specific date (e.g. "no lunch block today, we're working through it").
  Neither is required by the roadmap's stated P3-005 scope ("Lunches/
  recurring unavailable windows"). If a future need arises, the override
  case is the more likely one and should probably be solved by extending
  `AvailabilityException`'s existing one-off-date role (e.g. a flag meaning
  "suspend recurring blocks for this date"), not by adding more fields to
  `RecurringStaffBlock` itself — re-litigate as a new ADR if it comes up,
  rather than assuming this paragraph's sketch is the answer.
- P3-004 (one-off staff blocks) is **not** migrated to `RecurringStaffBlock`
  or changed by this ADR — its existing two-`AvailabilityException`-rows
  pattern remains correct for one-off dates (no staleness risk, since
  there's nothing in the future for it to drift out of sync with) and is
  explicitly a separate roadmap item (`feat/p3-004-staff-blocks-hardening`)
  scoped to validation/tests for the *existing* mechanism, not a model
  change.
- Implementation (model, migration, service wiring, API, tests) is tracked
  as a separate task, sequenced after `feat/p3-004-staff-blocks-hardening`
  per `docs/audits/pre-p3-readiness-audit.md` §10.
