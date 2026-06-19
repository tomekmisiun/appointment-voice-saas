# Pre-P3 Readiness Audit

## 1. Executive decision

**READY FOR P3 WITH BLOCKERS**

The MVP foundation (Epics A–L) and P2-001 through P2-012 are substantively
implemented, tested, and pass all repository validation gates
(`make validate-ai-workflows`, `make policy-guards`, ruff, 870/871 pytest with
the one failure confirmed flaky/order-dependent on rerun). The Alembic chain
is single-headed and safe against a populated database. P2-013 and P2-014 are
correctly documented as not implemented — no hidden implementation exists.

However, this audit found one **CRITICAL, pre-existing, repo-wide tenant
isolation gap** (single-resource `get_*`/`require_*` lookups filter by
`tenant_id` only, never `business_id`) that is newly exploitable through
P2's new GDPR-delete and CRM-client endpoints, plus a **HIGH-severity
concurrency gap** in the new waitlist offer/escalation logic (no row locking,
no idempotency guard — duplicate offers/SMS are possible under concurrent
cancellations or overlapping worker ticks). Both are narrow, well-understood,
single-PR-sized fixes. Neither requires re-architecting P2, and neither
blocks *planning* P3 — but the tenant-isolation gap must be fixed before any
further endpoints (P3-012 admin override, P3-001 salon hours API, etc.) are
built on the same insecure pattern, and the waitlist concurrency gap should
be fixed before pilot traffic relies on the waitlist.

P2-009 (combined-duration availability) and P2-008 (multi-service model) are
real, tested backend capabilities with **no caller-facing entry point** —
acceptable as foundation work, but the roadmap's "done" checkbox overstates
product-readiness; this should be corrected in roadmap wording, not treated
as a defect to fix immediately.

The P3 backlog is directionally still valid but the duplication-risk items
flagged by the original roadmap authors (P3-001/002/003/004) are confirmed
real and several P3 tasks need ADR-first sequencing (P3-005, P3-006, P3-014)
before implementation, as detailed in §9–10.

## 2. Repository baseline

- **Branch:** `audit/pre-p3-readiness` (created from `feat/p2-012-waitlist-timeout-escalation`, 2 commits ahead of `main`: `f8b136f` P2-012, `099265d` docs sync)
- **Commit SHA:** `099265d6d283367a71921abd4af0c6c54e3f608c`
- **Audit date:** 2026-06-19
- **Working-tree state:** clean at audit start; no unrelated changes present (no stop condition triggered)
- **Runtime assumptions:** Python ≥3.13 (`pyproject.toml:5`), PostgreSQL 17 (`docker-compose.yml:54,65`), Redis 7-alpine (`docker-compose.yml:74`), FastAPI + SQLAlchemy 2.0 + Alembic, Docker Compose local stack
- **Test count:** 871 collected; 870 passed, 1 failed on first full run, confirmed **passing in isolation** on rerun (flaky — see §7, §12)
- **Coverage:** 90.68% (floor 85%)
- **Validation results:** all green except the one flaky test (see §12 for full command output)

## 3. P2 task verification matrix

| Task | Roadmap status | Verified status | Evidence | Tests | Missing work | Severity |
|------|----------------|------------------|----------|-------|---------------|----------|
| P2-001 | [x] done | **PARTIALLY_IMPLEMENTED** | `app/models/client.py`, `app/services/client_service.py:47-52,120-141`, `app/api/routes/clients.py:57-102`, migration `p2001a2b3c4d5e` | `tests/test_avs_p2001_crm_clients.py` — tests tenant isolation, not cross-business | `get_client`/`require_client`/`update_client` filter by `tenant_id` only; routes never pass `business_id` to the service layer, so any client in the same tenant is readable/writable via any other business's URL prefix | **CRITICAL** (tenant→business isolation) |
| P2-002 | [x] done | **IMPLEMENTED** | `get_bookings_for_client()` `app/services/client_service.py:94-117`, no new `Booking` column (relies on `Client.customer_id` unique-per-business from P2-001) | `tests/test_avs_p2002_client_booking_history.py` — join correctness, ordering, null-customer, cross-customer exclusion all verified | Inherits P2-001's business-id gap (via `require_client`) | CRITICAL (inherited) |
| P2-003 | [x] done | **IMPLEMENTED** | `ivr_service.py` `_lookup_returning_caller_name()` calls `get_customer_by_phone()`/`get_client_by_customer_id()` — both correctly scoped by `business_id` **and** `tenant_id` | `tests/test_avs_p2003_ivr_returning_caller.py` incl. explicit cross-business test | None — correctly scoped, does not share P2-001's gap because it proactively passes `business_id` | None |
| P2-004 | [x] done | **PARTIALLY_IMPLEMENTED** | `GET /businesses/{business_id}/clients/{client_id}/bookings` `app/api/routes/clients.py:67-83` | `tests/test_avs_p2004_client_booking_history_api.py` — no cross-business test | Same root cause as P2-001: `business_id` accepted in path, never validated against the client's actual business | **CRITICAL** (inherited) |
| P2-005 | [x] done | **PARTIALLY_IMPLEMENTED** | `gdpr_delete_customer()` `app/services/customer_service.py:134-176` correctly anonymizes Customer+Client PII, preserves Booking FK (no `ON DELETE`), logs `AuditAction.CUSTOMER_ANONYMIZED` | `tests/test_avs_p2005_gdpr_delete.py` — PII scrub, FK preservation, audit log, admin-only all verified; no cross-business test | `gdpr_delete_customer()` filters by `tenant_id` only — same gap as P2-001/004, but here the consequence is anonymizing **another business's customer**, a privacy-incident-grade exposure | **CRITICAL** |
| P2-006 | [x] done | **IMPLEMENTED** | `IvrStep.STAFF_SELECTION`, `_schedulable_staff()`, `_handle_staff_selection()` in `ivr_service.py`; `availability_service.py` strict `staff_id` match, no business-level fallback; `selected_staff_id` threaded to `create_booking()` | `tests/test_avs_p2006_ivr_staff_selection.py` — 10 tests incl. 0/1/2+ staff, inactive exclusion, no-working-hours exclusion | None blocking; UX note: staff activated without working hours silently never appear in the menu (by design, but worth an onboarding warning) | LOW (UX) |
| P2-007 | [x] done | **IMPLEMENTED** | `get_last_staff_booking()` `booking_service.py:149-164` (business+tenant scoped), `_reorder_preferred_staff()` in `ivr_service.py` | `tests/test_avs_p2007_ivr_suggest_last_staff.py` incl. cross-business non-suggestion test | None | None |
| P2-008 | [x] done | **IMPLEMENTED** (backend-only) | `BookingLineItem` model, `add_booking_line_item()`/`list_booking_line_items()`/`get_booking_total_duration_minutes()` `booking_service.py:182-230`, migration `p2008a2b3c4d5e`; `Booking.service_id`/`ends_at` unchanged | `tests/test_avs_p2008_multi_service_booking.py` — 8 tests incl. cross-business/tenant denial | No API route, no IVR wiring — purely additive backend capability with zero callers today | MEDIUM (scope/tech-debt, not a bug) |
| P2-009 | [x] done | **PARTIALLY_IMPLEMENTED** | `get_available_slots_for_total_duration()` + shared `_get_available_slots_for_duration()` core `availability_service.py:64-192` | `tests/test_avs_p2009_combined_duration_availability.py` — 7 tests, incl. regression proof that single-service path is unaffected | Not called from `create_booking()`, the IVR flow, or any API route — roadmap itself documents this gap inline, but the checkbox reads "done" for an acceptance criterion ("availability uses combined duration") that has no product-facing effect yet | MEDIUM (documentation overstates product readiness) |
| P2-010 | [x] done | **IMPLEMENTED** | `WaitlistEntry` model (`WaitlistEntryStatus` plain-string enum), `create_waitlist_entry()`/`list_waitlist_entries()`/`update_waitlist_entry_status()` `waitlist_service.py`, migration `p2010a2b3c4d5e` with 4 indexes incl. composite `(business_id, service_id, desired_date)` | `tests/test_avs_p2010_waitlist_model.py` — 12 tests, cross-business/tenant denial verified | No unique constraint preventing duplicate WAITING entries for the same customer/service/date (acceptable if intentional, undocumented) | LOW |
| P2-011 | [x] done | **IMPLEMENTED** (with HIGH concurrency risk) | `cancel_booking()` calls `find_matching_waitlist_entries()` `waitlist_service.py:94-123`, offers oldest match, sets `offered_for_staff_id`, enqueues `WAITLIST_OFFER` via `enqueue_waitlist_offer()` — all inside the same DB transaction as the cancellation | `tests/test_avs_p2011_waitlist_offer_on_cancellation.py` — 10 tests, all sequential | `find_matching_waitlist_entries()` is a bare `SELECT` with no `.with_for_update()`/row lock and no unique constraint guarding the WAITING→OFFERED transition — two concurrent cancellations matching the same entry can both mark it OFFERED and both enqueue an SMS | **HIGH** (concurrency, no test coverage) |
| P2-012 | [x] done | **PARTIALLY_IMPLEMENTED** | `expire_stale_waitlist_offers()` + `_escalate_to_next_waiting_entry()` `waitlist_service.py:136-196`, wired into `run_scheduled_maintenance()` `app/worker.py:239`, `settings.waitlist_offer_timeout_minutes` (default 60) | `tests/test_avs_p2012_waitlist_timeout_escalation.py` — 8 tests incl. end-to-end P2-011→P2-012 chain, all sequential | The audit brief specifically calls out idempotency and concurrency for this task: neither is met — a second/overlapping maintenance tick (or a crash between commit and enqueue) can re-expire/re-escalate the same entry and double-send the next offer; no customer-facing "your offer expired" follow-up exists (product gap, not literally in scope, but undocumented); initial stale-offer query is not tenant/business-scoped (loads all tenants' OFFERED rows into one query, though escalation itself stays correctly scoped) | **HIGH** (idempotency/concurrency); LOW (cross-tenant query scope, no leak, just inefficient/visibility) |
| P2-013 | [ ] not done | **NOT_IMPLEMENTED** (confirmed) | No `metrics_service.py`/`export_service.py`, no `/metrics`/`/stats`/`/dashboard` business route; `app/api/routes/metrics.py` is Prometheus infra-metrics only | N/A | Entire feature | N/A — accurately documented |
| P2-014 | [ ] not done | **NOT_IMPLEMENTED** (confirmed) | No CSV/export route, model, or service found anywhere in `app/` | N/A | Entire feature | N/A — accurately documented |

**Verified completion count: 7 fully IMPLEMENTED (P2-002, 003, 006, 007, 008, 010, 011 — note P2-008/011 carry MEDIUM/HIGH caveats), 5 PARTIALLY_IMPLEMENTED (P2-001, 004, 005, 009, 012), 2 correctly NOT_IMPLEMENTED (P2-013, 014). Zero DUPLICATE_OR_ALREADY_COVERED, DOCUMENTATION_ONLY, or NO_LONGER_VALID findings among P2-001–014.**

No item was found to be **INCORRECTLY_MARKED_COMPLETE** in the sense of "nothing was built" — every `[x]` task has real, tested code. The closest case is P2-009, where the checkbox and "Acceptance" language imply product-level availability search that doesn't actually exist for any caller yet; treat this as a documentation-precision issue, not a fabricated task.

## 4. Cross-feature integration findings

- **Booking ↔ Waitlist:** `cancel_booking()` and the waitlist offer logic share one DB transaction (`booking_service.py:267-310`) — if `db.commit()` fails, neither the cancellation nor the offer happens (good). But the **job enqueue** (`enqueue_send_notification_job`) happens post-commit; if Redis is down at that instant, the entry is left OFFERED with no notification job ever sent. The next maintenance tick will eventually expire and re-escalate it, so this self-heals, but it's an undocumented "silent gap window."
- **Booking ↔ Multi-service (P2-008/009):** No regression — `create_booking()`, the double-booking exclusion constraint, calendar sync, and notifications are all untouched and still operate purely on `Booking.service_id`/`ends_at`. Verified via `test_single_service_search_unaffected_by_new_function()` and direct reading of `create_booking()`.
- **IVR ↔ CRM (P2-003/006/007):** All three correctly thread `business_id`+`tenant_id` end-to-end from `VoiceSession` through to `get_customer_by_phone()`/`get_client_by_customer_id()`/`get_last_staff_booking()`. This is the one area of P2 that does **not** share the tenant-isolation defect found in §3/§6 — these functions were written to take `business_id` explicitly rather than relying on a bare `get_by_id` helper.
- **GDPR ↔ Audit/Booking history:** Anonymization correctly avoids hard-delete (Booking FK has no `ON DELETE`, defaults to RESTRICT) and preserves the audit trail. Re-calling a since-anonymized phone number creates a brand-new `Customer` row (because `phone_normalized` becomes `f"deleted-{id}"`), which is correct GDPR behavior but is not explicitly tested for re-booking continuity.
- **Worker maintenance tick:** `run_scheduled_maintenance()` runs session-reset/reminder-enqueue/waitlist-expiry sequentially in one DB session inside one Redis lock. No isolation between sub-tasks; an exception in one could affect transaction state for the next within the same tick. Acceptable for current scale but worth hardening before P3-013 (reconciliation job) adds a fourth task to this list.
- **Notification outbox:** `WAITLIST_OFFER` reuses the existing `NotificationOutbox`/`enqueue_*` pattern faithfully — no duplicate-intent mechanism beyond what's described in §3/§7 for the race condition itself.
- **Calendar:** Untouched by any P2 work; one-way sync architecture (PostgreSQL source of truth) remains intact per ADR 0002.

## 5. Database and migration findings

**Chain integrity:** confirmed single linear head. `alembic heads` returns exactly one head: `p2012a2b3c4d5e`. Reconstructed order (oldest→newest, P2 portion): `p2001a2b3c4d5e` (clients) → `p2008a2b3c4d5e` (booking_line_items) → `p2010a2b3c4d5e` (waitlist_entries) → `p2012a2b3c4d5e` (waitlist_entries.offered_for_staff_id). No branching, no orphaned revisions.

Note: the local dev `db` container's `alembic current` reported `p2010a2b3c4d5e` (i.e., one migration behind head) at audit time — this is purely because `make migration-upgrade` hadn't been re-run against that persistent container since P2-012 landed; the test database used by pytest is provisioned fresh per run and is not affected. Not a defect, just stale local container state.

Per-migration findings:

| Migration | FKs | Indexes | Constraints | Backfill needed | Downgrade | Destructive ops |
|---|---|---|---|---|---|---|
| `p2001a2b3c4d5e` (clients) | `tenant_id`/`business_id` NOT NULL, `customer_id` nullable | tenant_id, business_id | `UNIQUE(business_id, customer_id)` — correctly business-scoped | No | Complete | None |
| `p2008a2b3c4d5e` (booking_line_items) | tenant/business/booking/service all NOT NULL | tenant_id, business_id, booking_id | `UNIQUE(booking_id, position)` | No | Complete | None |
| `p2010a2b3c4d5e` (waitlist_entries) | tenant/business/customer/service NOT NULL, staff_id nullable | tenant_id, business_id, status, composite `(business_id, service_id, desired_date)` | none beyond FKs | No | Complete | None |
| `p2012a2b3c4d5e` (offered_for_staff_id) | staff_id nullable FK | none added (correctly — not a filter column) | none | No (nullable) | Complete | None |

All four are additive, nullable-safe, and would apply cleanly to a populated production database with zero backfill or lock-duration risk. No `op.drop_*` calls anywhere in the new migrations — compliant with `.ai-rules/database.md`'s expand/contract rule. All FKs default to implicit CASCADE (no explicit `ondelete=`) — acceptable given tenant/business deletion is rare/controlled, but worth tightening to `RESTRICT` in a future hardening pass, not a P3 blocker.

## 6. Security and tenant-isolation findings

**FINDING 1 — CRITICAL — Cross-business data access within a tenant.**
`app/services/client_service.py:47-52` (`get_client`/`require_client`), `:120-141` (`update_client`), and `app/services/customer_service.py:83-95,134-176` (`get_customer`/`require_customer`/`gdpr_delete_customer`) all filter exclusively by `(id, tenant_id)`. The corresponding routes — `app/api/routes/clients.py:57-102` and `app/api/routes/customers.py:13-25` — accept `business_id` from the URL path but never pass it to the service layer for validation. Since `Business.tenant_id` is a foreign key (one tenant can own many businesses — confirmed via `app/models/business.py:36-38`), any authenticated user in a multi-business tenant can read or mutate **any other business's** `Client`, run a **GDPR anonymization on another business's `Customer`**, or read another business's client booking history, by simply substituting `business_id` in the URL while keeping a valid `client_id`/`customer_id`.

This is **not new to P2** — `app/services/staff_service.py:31-43` (`get_staff`/`require_staff`) and `app/services/booking_service.py:167-180` (`get_booking`/`require_booking`) show the identical pattern, confirming this is a pre-existing, repo-wide architectural gap already tracked (and left open) as **P4-001/P4-002/P4-003** ("audit product multi-tenancy queries," "add product tenant guards," "cross-tenant leakage tests"). What P2 changed is the **blast radius**: it added a GDPR-erasure endpoint and a CRM PII store on top of the same insecure pattern, turning a latent gap into one with privacy-incident-grade consequences (irreversible anonymization of the wrong business's customer).

**FINDING 2 — HIGH — Waitlist offer race condition (see §3/§7 for detail).** No row-level locking or uniqueness guard around the WAITING→OFFERED transition in `find_matching_waitlist_entries()`.

**FINDING 3 — HIGH (defense-in-depth) — Twilio voice keypress handler.** `app/api/routes/twilio_voice.py:150` looks up `VoiceSession` by `session_id` alone, not also validating it belongs to the `business_id` in the URL. Mitigated today by mandatory Twilio signature validation (`app/core/twilio_security.py`), but it's a second layer that's missing if signature validation is ever misconfigured or bypassed.

**FINDING 4 — MEDIUM — GAP-009 (phone masking) remains open, not worsened.** Grepped all new P2 service files (`client_service.py`, `waitlist_service.py`, GDPR/customer code, new IVR staff-selection code) — none log raw phone numbers. `TECH_DEBT.md` GAP-009 is still open repo-wide but P2 did not add new instances.

**FINDING 5 — LOW/forward-looking — Unbounded export risk for P2-014.** All current P2 list endpoints (`clients`, waitlist) correctly cap `size` at 100 via `Query(..., le=100)`. No current violation, but when P2-014 (CSV export) is eventually built it must not reuse a code path that bypasses this cap (e.g., a "give me everything" export mode), and must add formula-injection sanitization (leading `=`/`+`/`-`/`@` in cell values) since none of that logic exists yet anywhere in the repo to inherit from.

## 7. Test-quality findings

**Behavior proven (real, end-to-end, multi-row tests):**
- P2-001–002 customer/business tenant-isolation (single-tenant-many-business case excluded — see below)
- P2-003 returning-caller matching, including explicit cross-business non-match test
- P2-006/007 full IVR state-machine transitions (0/1/2+ staff, inactive exclusion, no-working-hours exclusion, reordering, cross-business non-suggestion)
- P2-008 line-item CRUD, position ordering, cross-business/cross-tenant denial
- P2-009 combined-duration slot math, staff filtering, regression-safety of the single-service path
- P2-010 waitlist CRUD and cross-business/tenant denial
- P2-005 GDPR PII scrubbing, FK preservation, audit-log emission, admin-only enforcement

**Behavior weakly tested (claims exist, but proof is thin):**
- **Cross-business (same-tenant) isolation at the API layer:** every P2-001/002/004/005 test exercises either single-tenant-single-business happy paths or cross-*tenant* denial at the *service* layer. None create two businesses under one tenant and attempt the actual exploit path described in Finding 1. This is precisely why the bug went unnoticed.
- **Waitlist concurrency:** `test_avs_p2011_*`/`test_avs_p2012_*` are exclusively sequential — no thread/async-concurrent test exercises the double-offer race. The P2-012 test suite's "end-to-end P2-011→P2-012" test runs cancellation then *manually* calls the expiry function once; it does not simulate two overlapping calls.
- **Waitlist idempotency:** no test calls `expire_stale_waitlist_offers()` twice and asserts a single notification/no duplicate state transition.
- **GDPR audit-trail integrity:** verifies the `AuditLog` row is created and that `Booking` rows survive, but does not verify the booking's *content* (time/staff/service) is untouched or that the audit trail remains queryable/reconstructable after anonymization.

**Behavior untested:**
- The cross-business exploit path itself (Finding 1) — zero coverage.
- Stale-offer customer feedback (no test expects or disproves a "your offer expired" notification — the feature doesn't exist).
- No mocking-masks-the-behavior-under-test issues were found — all P2 tests use the real DB and real service functions (`grep` for `@patch`/`MagicMock` across `tests/test_avs_p2*.py` returned zero hits), which is good practice and consistent with `.ai-rules/testing.md`.

## 8. Documentation drift

- **PROJECT_STATUS.md / docs/appointment-saas-roadmap.md** mark P2-001 through P2-012 "done" without surfacing the cross-business isolation gap or the waitlist concurrency gap — both are real defects in shipped code, not just missing tests. Recommend adding both to `TECH_DEBT.md` (see §11) rather than rewriting the roadmap checkboxes, since the *features* are genuinely built — the gaps are correctness/security debt, which is what `TECH_DEBT.md` is for.
- **docs/appointment-saas-roadmap.md P2-009 row** states "Acceptance: Availability uses combined duration" as met, but no caller (IVR or API) ever invokes `get_available_slots_for_total_duration()`. The roadmap's own inline note ("not yet wired into create_booking() or the IVR flow itself") already discloses this — the drift is the checkbox/acceptance-criteria wording reading as "done" despite that disclosure, not a concealed fact.
- **PROJECT_STATUS.md "Readiness Assessment" table** correctly flags PRODUCTION_READY as "No" and lists the right blockers (admin-override audit, P2-013/014, billing, monitoring). This part of the documentation is accurate and does not need correction.
- No other material drift found between documentation claims and verified code for P2-001–014.

## 9. P3 backlog validation matrix

| P3 task | Current coverage | Dependencies | Overlap/duplication | Recommended action | Required tests |
|---|---|---|---|---|---|
| P3-001 Salon opening hours | `WorkingHours.staff_id` already nullable (`app/models/working_hours.py:24-26`); API already permits `staff_id=null` rows but doesn't document/distinguish the intent | None | None — infra ready, just unexercised | KEEP, narrow scope to API docs + tests, no model change | Business-level create/list tests |
| P3-002 Intersect salon/staff hours | **Not implemented** — `_get_available_slots_for_duration()` queries *either* business-level *or* staff-level hours, never both (`availability_service.py:106-115`) | P3-001 | None | REWRITE — implement actual intersection | Empty-when-closed, intersection-narrows-window, staff-without-own-hours-falls-back tests |
| P3-003 Salon closures/holidays | `AvailabilityException.staff_id` nullable and already excluded correctly in slot generation (`availability_service.py:120-137`) | P3-001 | None | KEEP — add API docs/validation + tests only | Business-wide closure, staff-specific override, precedence tests |
| P3-004 Staff time blocks | Same `AvailabilityException` model already supports one-off staff blocks today, already excluded in slot generation | None | **Conceptual overlap with P3-005** (recurrence) — needs a model decision before P3-005 starts | KEEP — add overlap-validation + tests only | One-off block creation/exclusion, no-cross-staff-effect tests |
| P3-005 Recurring staff blocks | **Not implemented** — no recurrence field on `AvailabilityException`; `WorkingHours.day_of_week` is the only existing recurrence mechanism and is semantically "available," not "blocked" | P3-004 (conceptually) | **High** — must decide: extend `AvailabilityException` with a recurrence rule, or add a new `RecurringBlock` model, before any code lands | REWRITE — write a short ADR first, then implement | Recurring exclusion across multiple days, timezone correctness, one-off override-wins tests |
| P3-006 Design deposits/prepayments | `Service.price_minor_units`/`currency` exist (`app/models/service.py:27-28`); `BookingStatus` has only `CONFIRMED`/`CANCELLED` — no hold/pending state | Blocks P3-007, P3-008 | None | KEEP as ADR-only task, no code | None (ADR review) |
| P3-007 Stripe payment links | Not implemented; no payment adapter exists | Hard-blocked on P3-006 | None — new adapter following the existing `SmsProvider`/`CalendarProvider` pattern | KEEP, sequence after P3-006 | Payment-link creation, currency, expiry tests |
| P3-008 Pending-payment booking state | Not implemented | Blocked on P3-006, P3-007 | Must coordinate with the double-booking exclusion constraint (does a pending-payment hold reserve the slot?) | KEEP, sequence after P3-007 | Hold creation/expiry/slot-release/payment-confirms tests |
| P3-009 Multilingual IVR prompts | **Not implemented** — every prompt is a hardcoded string literal directly in `ivr_service.py`; `IvrResponse` (`app/core/ivr.py:18-23`) has no prompt-key/locale abstraction | None | None, but real risk of duplicating every IVR branch if done naively | REWRITE — extract prompt-key abstraction first | Prompt resolution by locale, fallback-to-default, single-code-path-no-branching tests |
| P3-010 Private calendar visibility | `CalendarIntegration`/`CalendarEvent` exist but have **no visibility/privacy field**; sync currently has no busy/free-only mode | None | Relates to P3-011/P3-014 | REWRITE — add visibility enum + sync logic | Per-visibility-tier sync behavior tests |
| P3-011 Calendar conflict import spike | **Not implemented** — no `import_events()`/`get_busy_periods()` on the calendar adapter interface at all | Relates to P3-014 | High risk of scope creep into full two-way sync if not kept as a spike | KEEP as ADR/spike only, no implementation | None (ADR review) |
| P3-012 Manual admin override | **Not implemented** — confirmed via repo-wide `grep` for "override"; no route, no audit action, no model field exists. **P1-013's admin-override audit logging is explicitly blocked on this task.** | None | None | KEEP — implement with explicit reason/audit logging, unblocks P1-013 | Override-cancel, override-force-create, reason-required, audit-log, admin-only tests |
| P3-013 Integration reconciliation job | Retry/backoff/DLQ infra already exists (`app/core/job_queue.py`); `NotificationOutbox`/`CalendarEvent` already track status/attempts — no actual stale-record sweep exists yet | None | None — thin addition on top of existing infra, not new infrastructure | KEEP, small scope | Stale-record detection, no-touch-recent-records, metric-emission tests |
| P3-014 Two-way calendar sync ADR | ADR 0002 already establishes "PostgreSQL is source of truth, external calendar is a view" (`docs/adr/0002-appointment-voice-saas-architecture.md:27-36`) — no dedicated two-way-sync ADR exists yet | Should follow the P3-011 spike | High — any "yes" answer here would contradict the existing accepted architecture and needs to be argued explicitly, not just documented | KEEP — write the ADR, default recommendation should be to reject full two-way sync in favor of one-way import + conflict alerts | None (ADR review) |

No P3 item was found to be a true duplicate of already-shipped P2 work. The closest near-duplicates (P3-001 vs `WorkingHours`, P3-003/004 vs `AvailabilityException`) are correctly flagged in the roadmap's own "partial" annotations, and this audit confirms those annotations are accurate.

## 10. Recommended P3 execution order

Each task below is sized for one reviewable branch/PR. ADR-only tasks are deliberately small and sequenced first where they unblock implementation tasks.

1. **`fix/tenant-business-scoping`** (blocker fix, not a P3 task — see §11) — Scope: add `business_id` parameter to `get_client`/`require_client`/`update_client` (`client_service.py`), `get_customer`/`require_customer`/`gdpr_delete_customer` (`customer_service.py`), and audit `get_staff`/`require_staff`/`get_booking`/`require_booking` for the same fix since they share the pattern. Out of scope: any new feature, any P3 work. Acceptance: every business-scoped route rejects a same-tenant-different-business resource ID with 404. Tests: new cross-business-same-tenant denial test for every affected route. Dependencies: none — do this first.
2. **`fix/waitlist-offer-concurrency`** (blocker fix) — Scope: add `.with_for_update(skip_locked=True)` (or equivalent) to `find_matching_waitlist_entries()`'s use inside `cancel_booking()` and `_escalate_to_next_waiting_entry()`; make `expire_stale_waitlist_offers()` idempotent (e.g., re-check status before escalating, or track processed IDs within the tick). Out of scope: stale-offer customer notification (separate, P2-012 already shipped without it — track as tech debt, not a blocker). Acceptance: a concurrency test with two simulated concurrent cancellations only results in one OFFERED transition. Tests: new concurrency test in `tests/test_concurrency.py` or a new `test_waitlist_concurrency.py`. Dependencies: none.
3. **`feat/p3-012-admin-override`** — Scope: admin override cancel/force-create routes, `AuditAction.BOOKING_OVERRIDE_*`, reason-required validation. Out of scope: frontend UI. Acceptance: overrides are admin-only, reasoned, audited, and unblock P1-013's remaining gap. Tests: override-cancel frees slot, force-create allows overbooking with audit trail, reason required, non-admin denied. Dependencies: #1 above (don't add a new admin route on the unfixed pattern).
4. **`feat/p3-009-ivr-prompt-keys`** — Scope: extract all `ivr_service.py` prompt strings into a locale-keyed lookup with English as the only populated locale (no translation content yet — this task is the architecture, not the translations). Out of scope: actual non-English text. Acceptance: zero hardcoded prompt strings remain inline; adding a second locale requires zero changes to step-handler logic. Tests: prompt resolution by key, fallback-to-default-locale, single-code-path test. Dependencies: none.
5. **`docs/adr-recurring-staff-blocks`** — Scope: ADR deciding `AvailabilityException` extension vs. new `RecurringBlock` model for P3-005. Out of scope: implementation. Acceptance: ADR accepted. Dependencies: none.
6. **`feat/p3-004-staff-blocks-hardening`** — Scope: overlap validation + dedicated test suite for the *already-working* one-off staff block path. Out of scope: recurrence (waits for #5's ADR). Acceptance: overlapping-block validation behavior is explicit and tested. Dependencies: none.
7. **`feat/p3-001-salon-hours-api`** — Scope: document/clarify the existing nullable-`staff_id` business-hours capability at the API layer; add tests. Out of scope: intersection logic (that's #8). Acceptance: admin can create and retrieve business-level hours distinctly from staff hours. Dependencies: none.
8. **`feat/p3-002-hours-intersection`** — Scope: implement actual business∩staff hours intersection in `_get_available_slots_for_duration()`. Out of scope: P3-003 exception precedence rules beyond what already works. Acceptance: a slot only appears when both salon and staff are open. Tests: closed-salon/open-staff returns empty; intersection narrows the window correctly. Dependencies: #7.
9. **`feat/p3-003-salon-closures`** — Scope: validation + test suite for the *already-working* business-wide `AvailabilityException` path; document precedence (business closure always wins over staff availability). Out of scope: new model fields. Dependencies: #7, #8.
10. **`feat/p3-005-recurring-blocks`** — Scope: implement the model/migration/service/API/tests per the ADR from #5. Dependencies: #5, #6.
11. **`feat/p3-013-reconciliation-job`** — Scope: new maintenance-tick job sweeping stale `NotificationOutbox`/`CalendarEvent` rows, with metrics. Out of scope: auto-repair beyond re-queueing. Dependencies: none — can run in parallel with the hours/blocks track.
12. **`docs/adr-deposits-architecture`** (P3-006) — Scope: ADR only. Dependencies: none.
13. **`docs/adr-calendar-import-spike`** (P3-011) — Scope: ADR/spike only, interface sketch, no implementation. Dependencies: none.
14. **`docs/adr-two-way-calendar-sync`** (P3-014) — Scope: ADR only, should explicitly reference and either reaffirm or amend ADR 0002. Dependencies: #13.
15. **`feat/p3-010-calendar-visibility`** — Scope: visibility field + sync-mode logic. Dependencies: #13 informs whether import needs the same field.
16. **`feat/p3-007-stripe-payment-links`** — Scope: Stripe adapter + payment-link route. Dependencies: #12.
17. **`feat/p3-008-pending-payment-state`** — Scope: new booking status, hold-expiry worker job. Dependencies: #16.

## 11. Blockers before P3

**Must fix before any P3 work:**
- Cross-business tenant-isolation gap (Finding 1, §6) — any new P3 route built on `get_*`/`require_*` helpers will inherit this bug if not fixed first. Fix is branch #1 in §10.

**Must fix before a related P3 task:**
- Waitlist offer concurrency/idempotency (Finding 2, §6) — not strictly required before P3 starts (it doesn't block planning or unrelated P3 branches), but must be fixed before pilot traffic depends on the waitlist, and ideally before any P3 work that touches `waitlist_service.py` or the worker maintenance tick (e.g., P3-013's reconciliation job will share that tick).
- Twilio voice keypress defense-in-depth (Finding 3, §6) — low urgency given signature validation already mitigates it, but should be fixed alongside #1 since it's the same class of fix.

**Can be deferred:**
- P2-008/P2-009 lack of caller-facing entry points — acceptable foundation work; wire up when an actual multi-service product requirement appears.
- Stale-offer customer notification gap (no "your offer expired" SMS) — real UX gap, not a correctness defect; track in `TECH_DEBT.md`.
- GAP-009 (phone masking in logs) — pre-existing, unrelated to P2, no new instances introduced.
- FK `ondelete=` hardening on new P2 tables — cosmetic robustness improvement, not urgent.

## 12. Validation evidence

| Command | Exit status | Result | Notes |
|---|---|---|---|
| `bash scripts/validate-ai-workflows.sh` | 0 | PASS | "all required AI workflow files present" |
| `bash scripts/ci/run_policy_guards.sh` | 0 | PASS | model-migration-pair ok, pyproject-lock-pair ok (no dep changes), migration-drops ok, ci-gate-regression ok, ai-commit-trailers ok |
| `docker compose run --rm api alembic heads` | 0 | PASS | single head: `p2012a2b3c4d5e` |
| `docker compose run --rm api alembic current` (dev `db` container) | 0 | INFORMATIONAL | reported `p2010a2b3c4d5e` — local container one migration behind head; not a chain defect, just stale local state pre-`migration-upgrade` |
| `docker compose run --rm api ruff check .` | 0 | PASS | "All checks passed!" |
| `docker compose run --rm api pytest --cov=app --cov-report=term-missing -q` | 1 | 870 passed, 1 failed | `test_notification_job_is_not_blocked_by_calendar_backlog` failed on full-suite run |
| `docker compose run --rm api pytest tests/test_worker.py::test_notification_job_is_not_blocked_by_calendar_backlog -q` (isolated rerun) | 0 | PASS | Confirms the failure is order/shared-real-Redis-state-dependent (the test's own docstring acknowledges this risk), not a P2-012 regression — it covers P1-009 round-robin queue behavior, unrelated to any P2 code path. Pre-existing test-isolation fragility, not introduced by this audit's branch. |
| Coverage | — | 90.68% | floor is 85%, comfortably exceeded |
| `pytest --collect-only -q` | 0 | 871 tests collected | matches PROJECT_STATUS.md's stated count |

## 13. Final recommendation

Start with **`fix/tenant-business-scoping`** (§10, item 1) before any other work, including any P3 branch. This is the single highest-leverage fix: it is small, mechanical, fully covered by straightforward new tests, and removes a CRITICAL, currently-exploitable data-isolation bug before P3 adds more routes that would otherwise copy the same insecure pattern (most directly, P3-012's admin override). Follow immediately with `fix/waitlist-offer-concurrency` (§10, item 2) before the waitlist carries real pilot traffic. Only after both land should P3 feature branches begin, starting with `feat/p3-012-admin-override` (unblocks the long-pending P1-013 audit gap) and the salon-hours track (`feat/p3-001-salon-hours-api` → `feat/p3-002-hours-intersection` → `feat/p3-003-salon-closures`).
