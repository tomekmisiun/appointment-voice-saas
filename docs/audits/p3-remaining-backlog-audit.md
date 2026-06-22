# P3 Remaining-Backlog and Documentation-Accuracy Audit

## 1. Executive summary

**Scope:** what's left in the P1–P4 production-expansion backlog after P3-005
(recurring staff blocks, PR #58, merged 2026-06-22), and whether
`TECH_DEBT.md`/`PROJECT_STATUS.md`/`README.md`/`ROADMAP.md` still accurately
describe the current state. This is a documentation/planning audit, not a
code-security audit — see `docs/audits/pre-p3-readiness-audit.md` for the
last code-level security/tenancy review (2026-06-19/22).

**Backlog status (52 P1–P4 items):** 33 fully implemented or covered, 4
partially implemented (P4-001/002/003 tenancy-audit related, plus P4-004),
15 not started. One genuine duplicate was found: **P4-005** ("onboarding
wizard API: staff/service/hours guided setup endpoints") is already fully
covered by AVS-L004's `POST /api/v1/onboarding`, shipped earlier in EPIC L
and never reconciled against the P4 backlog (§4). P4-004 is correspondingly
downgraded from "not started" to **partial** — the same endpoint covers its
"setup business profile" half, but not the "signup" half (provisioning a
brand-new tenant/admin account, which is still a manual step per
`docs/runbooks/pilot-onboarding.md`).

**Documentation finding:** six `TECH_DEBT.md` items (AVS-TD-005, AVS-TD-010,
AVS-TD-011, AVS-TD-012, AVS-TD-015, AVS-TD-022) were marked **Open** despite
the roadmap tasks they track being fully implemented and merged — confirmed
by direct code inspection (§3); corrected to Done. A seventh (AVS-TD-016)
was also Open but only *part* of its listed scope (SMS/calendar provider
failures, worker DLQ backlog) is actually implemented — booking-failure and
IVR-failure-specific metrics, which the row's Recommendation also lists, do
not exist; corrected to **In Progress** rather than Done, to avoid
overstating coverage. The first six are pure tracking-file staleness, not a
product gap — the underlying features exist and work; all six cluster in
the same two roadmap tiers (P1 and the P3-001–005 salon-hours track),
suggesting `TECH_DEBT.md` simply wasn't revisited when those tiers shipped,
not an isolated oversight. `README.md` and `ROADMAP.md` are also materially
stale — both still describe the product in a pre-implementation planning
voice ("Appointment Voice SaaS runtime is not implemented yet") despite 32
backlog items plus the full MVP foundation being done (§5). All findings are
corrected in this change set.

**Process note:** the first verification pass only spot-checked the rows
flagged by an initial read-through and missed AVS-TD-010/011/012 (same
staleness pattern, same P1 tier) — caught by the cross-provider Reviewer on
a later pass, not by the initial audit. §3's table reflects the corrected,
exhaustive pass: every `Open`/`In Progress` row in `TECH_DEBT.md` was
checked against its "Related roadmap task" column's current `[x]`/`[ ]`
status, not just a sample.

**Recommended next task:** `feat/p3-013-reconciliation-job` (P3-013) — the
next item in `pre-p3-readiness-audit.md` §10's execution order (its item
11), which remains valid and is **not** reordered by this audit (items 1–10
of that order are now done — see §6 for why P3-013 stays ahead of P3-006).

## 2. Method

- Read `docs/appointment-saas-roadmap.md` (all 52 P1–P4 rows + audit notes),
  `TECH_DEBT.md`, `PROJECT_STATUS.md`, `README.md`, `ROADMAP.md`,
  `docs/audits/pre-p3-readiness-audit.md` in full.
- For every `TECH_DEBT.md` row marked **Open**, grepped the codebase for the
  artifact the "Recommendation" column says is missing, to confirm the
  status is still accurate rather than trusting the table.
- For every roadmap row marked `[ ]` (not done) in P2-013/014, P3-006/007/
  008/010/011/013/014, and all of P4, grepped for the obvious model/service/
  route name to confirm no hidden implementation exists.
- Did not re-run the full pytest suite or re-derive tenant-isolation findings
  already covered by `pre-p3-readiness-audit.md` — that audit's code-level
  findings (Findings 1–5, §6) are unrelated to documentation accuracy and
  remain valid as written; this audit only checks whether their tracked
  *status* is still correct.

## 3. TECH_DEBT.md status corrections

| ID | Table row said | Verified | Evidence |
|----|----------------|----------|----------|
| AVS-TD-005 | Open ("No notification outbox for product SMS/calendar side effects") | **Done** | `app/models/notification_outbox.py:29` (`NotificationOutbox`), `app/models/calendar_event.py:19` (`CalendarEvent`) — both implemented, tested, and already listed as done under EPIC E/F in the same roadmap file |
| AVS-TD-010 | Open ("No reminder SMS") | **Done** | `enqueue_due_reminders()` (`app/services/notification_service.py:172`) — P1-001 `[x]` in the roadmap already |
| AVS-TD-011 | Open ("No reschedule flow") | **Done** | `reschedule_booking()` (`app/services/booking_service.py:343`), used by both IVR self-service and admin reschedule — P1-003/004 `[x]` already |
| AVS-TD-012 | Open ("No IVR timeout or invalid-input fallback") | **Done** | `no_input_count`/`invalid_key_count` termination, `_REPEAT_KEYS` (`app/services/ivr_service.py`), `OperationalError`/`RedisError` graceful handling (`app/api/routes/twilio_voice.py:122`) — P1-005 to P1-008 all `[x]` already |
| AVS-TD-015 | Open ("No SMS/calendar retry/DLQ for product side effects") | **Done** | `app/core/job_queue.py:143` (`calculate_retry_delay_seconds`), `:325` (`get_failed_queue_depth`) — P1-009/010/011 all `[x]` in the roadmap already |
| AVS-TD-016 | Open ("No product monitoring/alerting") | **In Progress** (not fully Done) | `app/core/metrics.py:39-41` (`worker_failed_queue_depth`, `sms_provider_requests_total`, `calendar_provider_requests_total`), `observability/prometheus/rules/worker-alerts.yml` cover SMS/calendar/worker-DLQ; **no** booking-failure or IVR-failure-specific metric exists (`grep` for a booking/IVR `Counter` in `app/core/metrics.py` returns nothing) — the row's Recommendation lists both, so it cannot be marked fully Done |
| AVS-TD-022 | Open ("No salon hours versus staff hours intersection") | **Done** | P3-001 through P3-005 (its full "Related roadmap task" range) are now all `[x]` — `_intersect_time_windows()` and `_subtract_time_windows()` in `app/services/availability_service.py` |

No other `TECH_DEBT.md` row was found stale on the corrected, exhaustive
pass. Specifically checked and confirmed still **accurately Open**:
- **AVS-TD-028** (CalendarIntegration staff_id ownership) — no service or
  route anywhere creates a `CalendarIntegration` row (`grep -rln
  "CalendarIntegration(" app/services/ app/api/` returns nothing); the debt
  item's own recommendation ("when the service that creates these rows is
  added...") never triggered, so it correctly remains open and dormant.
- **AVS-TD-031** / **GAP-013** (VoiceSession lookup not business-scoped) —
  `app/api/routes/twilio_voice.py`'s keypress handler still queries
  `VoiceSession.id == session_id` alone, no `business_id` filter.
- **GAP-009** (phone masking in logs) — no masking helper exists anywhere in
  `app/core/logging.py` or `app/core/log_helpers.py`; still open, unchanged
  since the pre-P3 audit's Finding 4.

This change set flips the six corrected rows to `Done` (and AVS-TD-016 to
`In Progress`) in `TECH_DEBT.md` with a one-line evidence note each, per
`.ai-rules/documentation.md`'s rule that closing an item must update its
Status in the same change set.

## 4. Remaining backlog (verified not implemented)

Confirmed via direct grep — no hidden implementation found for any of the
following (all still correctly `[ ]` in the roadmap). The one exception,
**P4-004/005**, is called out separately at the end of this section: P4-005
turned out to already be done (now `[x]`) and P4-004 partial, not unstarted
— everything else below remains genuinely not implemented.

**P2 (2 items):** P2-013 (owner metrics API), P2-014 (CSV export). No
`metrics_service.py`/`export_service.py`/CSV route exists; the existing
`app/api/routes/metrics.py` is Prometheus infra-metrics only, unrelated.

**P3 (7 items):** P3-006 (deposits/prepayments ADR), P3-007 (Stripe payment
links), P3-008 (pending-payment booking state) — no `deposit`/`prepayment`
reference, Stripe SDK usage, or payment-link route anywhere in `app/`.
(`app/core/webhook_security.py` has a `STRIPE_STYLE_SIGNATURE_PATTERN`
helper, but it's a generic, provider-neutral HMAC-signature verifier that
happens to follow Stripe's `t=...,v1=...` header convention — inherited
foundation code, not a Stripe payments integration; no `stripe` SDK import
or API call exists anywhere.) P3-010 (calendar visibility
rules), P3-011 (calendar conflict import spike) — only ADRs 0001–0003 exist
in `docs/adr/`, none address calendar privacy or import. P3-013
(reconciliation job) — no `reconcil*` match anywhere in `app/`. P3-014
(two-way calendar sync ADR) — not in `docs/adr/`.

**P4 (6 fully unstarted + 4 partial/covered):** P4-006 through P4-011 (phone
provisioning, Stripe Billing, plan limits, billing webhooks, plan-limit
blocking, compatibility checklist) — no `Subscription`/Stripe model
anywhere in `app/models/`. P4-001/002/003 (tenancy query audit, tenant
guards, leakage tests) remain genuinely **partial**:
`tests/test_product_tenant_isolation.py` and `require_business()` exist and
work, but no systematic per-query checklist, no standardized tenant-guard
dependency, and no CI-enforced per-route isolation-test requirement exist
yet — this matches the roadmap's own "partial" notes and needed no
correction.

**P4-004/005 — duplicate/partial finding:** unlike the rest of P4, these two
were *not* simply unstarted. `app/api/routes/onboarding.py` +
`app/services/onboarding_service.py` (`POST /api/v1/onboarding`, shipped
under AVS-L004) already creates a business with staff, services, and
working hours in one call. That fully satisfies **P4-005**'s scope ("Staff/
service/hours guided setup endpoints") — a straight duplicate, corrected to
`[x]` Done in the roadmap. It only *partially* satisfies **P4-004**'s scope
("Signup/setup business profile"): the "setup business profile" half is
covered by the same endpoint, but the "signup" half — a brand-new salon
owner provisioning their own tenant/admin account without one already
existing — is not; `docs/runbooks/pilot-onboarding.md` still documents this
as a manual operator step. Corrected to `partial` in the roadmap.

No other P3/P4 item overlaps already-shipped work; no other item should be
removed from the backlog as no-longer-relevant.

## 5. README.md / ROADMAP.md drift

Both files still read as pre-implementation planning documents:

- `README.md` "Current Status" / "What Is Implemented" / "What Does Not
  Exist Yet" describe the state "As of Epic I / Epic J" and list IVR, SMS
  outbox, calendar adapter, and call transfer as **planned** — all of these
  have been done for multiple sessions; the MVP foundation, all P1/P2 work,
  and 7 of 14 P3 items are also unmentioned.
- `ROADMAP.md` "Current State" states "Appointment Voice SaaS runtime is not
  implemented yet" and "No product database models, migrations, booking
  engine, availability engine, IVR, SMS, calendar sync, transfer, billing,
  frontend, or product smoke tests exist yet" — none of this is true. Its
  "Next Recommended Execution Order" still lists `AVS-A002`/`AVS-B001`
  through `AVS-B009`, all done since the MVP foundation phase.

Both are corrected in this change set to reflect verified current status,
pointing to `PROJECT_STATUS.md` and `docs/appointment-saas-roadmap.md` as the
sources of truth rather than restating per-task detail (per
`.ai-rules/documentation.md`: "Do not duplicate rule/content bodies").

## 6. Recommended order for remaining work

Unchanged from `pre-p3-readiness-audit.md` §10, items 11–17, renumbered to
start after P3-005 (items 1–10 of that order are now done). This audit does
**not** reorder it — `feat/p3-013-reconciliation-job` is independent of the
deposits/payments track and was already sequenced ahead of
`docs/adr-deposits-architecture` in the original plan, specifically so it
can land in parallel with (not blocked by) the hours/blocks track that just
finished:

1. `feat/p3-013-reconciliation-job` — thin addition on top of existing
   retry/DLQ infrastructure (`app/core/job_queue.py`); no dependency on any
   other remaining item.
2. `docs/adr-deposits-architecture` (P3-006) — ADR only, no code. Unblocks
   P3-007/008.
3. `docs/adr-calendar-import-spike` (P3-011) — ADR/spike only.
4. `docs/adr-two-way-calendar-sync` (P3-014) — ADR only, should explicitly
   reference and either reaffirm or amend ADR 0002; sequence after #3.
5. `feat/p3-010-calendar-visibility` — depends on whatever #3 decides about
   import needing the same visibility field.
6. `feat/p3-007-stripe-payment-links` — depends on #2.
7. `feat/p3-008-pending-payment-state` — depends on #6.
8. P2-013/P2-014 (owner metrics, CSV export) and P4-001 through P4-011
   (tenancy hardening, billing) were always sequenced after the P3
   operational-extensions tier per the roadmap's own tier ordering; no new
   information from this audit changes that (P4-005 is already done — §4).

## 7. Validation

This is a docs-only change set (`TECH_DEBT.md`, `PROJECT_STATUS.md`,
`README.md`, `ROADMAP.md`, `docs/appointment-saas-roadmap.md` audit-notes
section, this file). No `app/`, `tests/`, or `alembic/` files changed.

| Command | Result |
|---|---|
| `bash scripts/validate-ai-workflows.sh` | PASS |
| `bash scripts/ci/run_policy_guards.sh` | PASS |

No `make validate` run — no runtime code, tests, dependencies, or migrations
changed (per `.ai-rules/agent-orchestration.md` §6, docs-only changes
require no pytest run).
