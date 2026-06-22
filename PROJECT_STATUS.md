# Project Status — Appointment Voice SaaS

Verified as of 2026-06-22.

## Current Status

All MVP foundation epics (A–K) and full Epic L (L001–L004, owner acquisition + onboarding) implemented. Production expansion backlog P1-001 through P1-013 and P2-001 through P2-012 (CRM, preferred staff, multi-service bookings, waitlist with offer/timeout/escalation) done. Both pilot-blocking gaps found in the pre-P3 audit (cross-business tenant isolation, waitlist offer concurrency) are fixed, plus a related cross-business gap found independently in working-hours/availability-exceptions (GAP-014/AVS-TD-032) — also fixed. P3-012 (manual admin override), P3-009 (multilingual IVR prompt architecture), P3-004 (staff time block overlap validation), P3-001 (salon opening hours API — found and closed a real gap: staff-specific working hours had no API path at all), P3-002 (salon/staff hours intersection — found and fixed a related gap: staff with no individual schedule used to get zero availability instead of falling back to the salon's hours, which had silently neutered IVR per-staff selection in the demo data), P3-003 (salon closures API clarity + precedence/isolation tests), and P3-005 (recurring staff blocks — new `RecurringStaffBlock` model per ADR 0003, subtracted from generated slots as a third precedence step after `WorkingHours`/`AvailabilityException`, verified to stay correct when working hours change later) are done. 974 tests collected and passing. CI green.

The product can be fully demonstrated locally using fake SMS and fake calendar
providers. Real Twilio voice and SMS providers are wired and configured via env
vars. A pilot can be set up against the `docs/mvp-pilot-deployment-checklist.md`.

## Verified Capabilities

### Foundation (inherited, running)

- FastAPI app, versioned routes, middleware, health checks, metrics, OpenAPI.
- PostgreSQL + SQLAlchemy + Alembic migrations.
- Redis-backed rate limiting, caching, idempotency, job queue.
- JWT auth, RBAC, user management, multi-tenant foundation.
- Webhook verification + idempotency pattern.
- Background worker with retries, delayed jobs, failed-job handling.
- Docker Compose local stack, CI (pre-commit, pytest, Trivy, coverage ≥85%).

### Core SaaS Domain (EPIC B — done)

- **Business** model/service/API (`/api/v1/businesses`). Transfer settings (enabled, policy, phone).
- **Staff** model/service/API (`/api/v1/businesses/{id}/staff`). Active status, phone.
- **Service** model/service/API (`/api/v1/businesses/{id}/services`). Duration, price.
- **WorkingHours** model/service/API. Day/time windows, staff or business scope.
- **AvailabilityException** model/service/API. One-off overrides.
- **Customer** model/service. Phone normalisation, race-safe deduplication within business.
- **Booking** model/service/API (`/api/v1/businesses/{id}/bookings`). CONFIRMED/CANCELLED lifecycle.
- Alembic migrations, tenant indexes, FK constraints.
- `EXCLUDE USING gist` (btree_gist) constraint for DB-level double-booking prevention.
- Booking audit logs (create/cancel/source/actor) via `AuditLog`.
- Tenant isolation tests for all product tables (`tests/test_product_tenant_isolation.py`).

### Availability Engine (EPIC C — done)

- Slot generation from service duration + working hours (`app/services/availability_service.py`).
- Confirmed booking exclusion (half-open interval overlap).
- Availability exception overlay (closures → empty; special hours → override).
- Timezone/DST handling via `zoneinfo.ZoneInfo` — summer/winter offset tests pass.
- Availability API (`GET /api/v1/businesses/{id}/availability`).
- Full test coverage including cross-tenant and cross-business isolation.

### Notification Outbox + Fake SMS (EPIC E — done)

- `NotificationOutbox` model. Intent stored before delivery.
- Provider-neutral SMS interface (`SmsProvider` Protocol).
- `NullSmsProvider` (logs not configured), `FakeSmsProvider` (records for tests).
- `TwilioSmsProvider` (real production adapter, activated by env vars).
- Booking confirmation and cancellation enqueue intents for customer + business.
- Notification worker processes `send_notification` jobs.
- Retry/backoff: after `MAX_NOTIFICATION_ATTEMPTS`, row marked `FAILED`.

### Calendar Adapter (EPIC F — done)

- `CalendarProvider` Protocol interface.
- `CalendarIntegration` model (business/staff calendar config).
- `CalendarEvent` table (booking → provider event lifecycle).
- `FakeCalendarProvider` (records operations for tests).
- Calendar event created after booking (via worker).
- Cancellation/update reflected through adapter.
- Retry/DLQ tests: `tests/test_calendar_worker.py`.

### Voice/IVR Simulation (EPIC G — done)

- `VoiceSession` model (step, caller_phone, selections, expiry, transfer_destination).
- `IvrResponse` abstraction (provider-neutral prompts, options, action, transfer_destination).
- Simulation endpoints (`POST /api/v1/ivr/simulate/call`, `/press`).
- Main menu: press 1 to book, press 2 to transfer.
- Service keypad selection (up to 9 services).
- Slot proposal keypad (available slots).
- Booking confirmation from IVR.
- No-slots terminal path (`NO_SLOTS` step).
- Invalid key re-prompt at every step.
- Session expiry: `expires_at` enforced at handle_keypress; `expire_stale_sessions()` wired to worker.
- E2E IVR test: `tests/test_ivr_e2e.py`.

### Real Provider Integrations (EPIC H — done)

- Twilio voice webhook adapter (`app/services/twilio_voice_adapter.py`): IvrResponse → TwiML.
- Twilio voice webhook route (`/api/v1/webhooks/twilio/voice/{business_id}`).
- Twilio signature validation (`app/core/twilio_security.py`).
- Twilio SMS provider (`TwilioSmsProvider` in `sms_provider.py`).
- SMS status webhook (`/api/v1/webhooks/twilio/sms/status`).
- Provider webhook idempotency via `idempotency_service`.
- Public webhook IP-aware rate limiting.
- Twilio provider runbook: `docs/twilio-provider-runbook.md`.

### Call Transfer (EPIC I — done)

- Business transfer settings (enabled/disabled, policy: business_phone or staff).
- `BusinessTransferHours` model + API (configurable transfer windows).
- Staff eligibility: active staff with non-null, non-whitespace phone.
- IVR press-2 branch: resolves destination per policy, emits TRANSFER action.
- TRANSFER_UNAVAILABLE fallback (returns to main menu).
- Tests: `tests/test_avs_i001_transfer_hours.py` through `test_avs_i005_transfer_coverage.py`.

### Demo and MVP Readiness (EPIC J — done)

- `make seed-demo`: deterministic demo seed (Glamour Studio Demo, 3 staff, 3 services, Mon–Sat).
- Manual booking smoke: `tests/test_avs_j002_smoke_manual_booking.py`.
- IVR simulated booking smoke: `tests/test_avs_j003_smoke_ivr_booking.py`.
- Cancellation smoke: `tests/test_avs_j004_smoke_cancellation.py`.
- README demo scenario documented.
- MVP pilot deployment checklist: `docs/mvp-pilot-deployment-checklist.md`.

### Self-Service Onboarding API (AVS-L004 — done)

- `POST /api/v1/onboarding` — atomic one-call setup: business + staff + services + working hours in one request. Requires admin role.
- `DELETE /api/v1/businesses/{id}/services/{service_id}` — hard delete for services.
- `PATCH /api/v1/businesses/{id}/working-hours/{wh_id}` — update start/end time; validates end > start.
- `OnboardingSetupRequest` schema with full validation (external mode URL required, hour range check).
- `setup_business_onboarding()` service orchestrates creation across four existing service layers.
- 22 tests in `tests/test_avs_l004_self_service_onboarding.py`. No migration needed — no new models.

### Owner Dashboard Skeleton (AVS-L003 — done)

- Scope document: `docs/product/owner-dashboard.md`.
- Defines 7 dashboard pages (home, bookings, settings, staff, services, working hours, exceptions) with required API routes per page.
- Identifies 5 API gaps (single booking read, staff PATCH, service PATCH/DELETE, working hours PATCH/DELETE, exception DELETE) — all CRUD completions, no new models.
- Auth/tenancy requirements documented: existing `require_business()` pattern applies to all gap endpoints.
- No runtime code changes — docs and gap analysis only.

### Manual Pilot Onboarding Runbook (AVS-L002 — done)

- Operator runbook: `docs/runbooks/pilot-onboarding.md`.
- Covers full lifecycle: lead review → qualify → create tenant/business → configure IVR → verify via simulation → hand off.
- Two paths: external booking link (minimal setup) and standalone booking (staff, services, working hours).
- Includes IVR simulation verification checklist, notification outbox check, troubleshooting table.
- No runtime code changes — docs only.

### Owner Lead Intake (EPIC L / AVS-L001 — done)

- Public pilot lead intake endpoint: `POST /api/v1/owner-leads` (no auth, rate-limited 5/hr/IP).
- `OwnerLead` model — not tenant-scoped (prospective new tenants).
- Fields: business_name, owner_name, email, phone_number/normalized, city, booking_mode_interest, external_booking_url, message, status.
- `booking_mode_interest` enum: `external_booking_link`, `standalone_booking`, `unsure`.
- `status` lifecycle: `new → contacted → qualified → onboarded / rejected`.
- Admin endpoints: `GET /api/v1/owner-leads`, `GET /api/v1/owner-leads/{id}`, `PATCH /api/v1/owner-leads/{id}/status`.
- URL validation (http/https only, no newlines), email validation, phone normalization.
- Public response exposes only safe fields (no email/phone/message).
- Migration: `l001a2b3c4d5e`.
- 35 tests in `tests/test_avs_l001_owner_lead.py`.
- Docs: `docs/product/owner-acquisition.md`.

### Booking Mode and Subscription Plan (EPIC K — done)

Two independent dimensions added to `Business`:

- **`booking_mode`** (operational): `internal_booking` (default) or `external_booking_link`.
  - `internal_booking`: press 1 drives full internal service→slot→booking flow (unchanged).
  - `external_booking_link`: press 1 sends SMS with `external_booking_url` and ends call (`EXTERNAL_LINK_SENT` terminal step). No Booking row is created.
- **`subscription_plan`** (commercial): `booksy_lite`, `booksy_pro`, `full_booking` (default), `full_booking_pro`. Stored only — no feature enforcement yet.
- `external_booking_url`, `external_booking_label`, `external_booking_provider` fields for the external link.
- `BusinessCreate` model_validator: `external_booking_url` required when `booking_mode=external_booking_link`.
- `PlanPolicyService` stub (`app/services/plan_policy_service.py`): single seam for future billing enforcement.
- `enqueue_external_booking_link_sms()` in notification service: `booking_id=None`, purpose=`EXTERNAL_BOOKING_LINK`.
- IVR main menu prompt is mode-aware.
- Migration: `k001a2b3c4d5e` — all 5 columns with `server_default` for backward compat.
- 18 tests in `tests/test_avs_k001_booking_mode.py`.

## Known Limitations and Gaps

| ID | Gap | Severity | Status |
|----|-----|----------|--------|
| BUG-001 | ~~Twilio keypress route used `business.phone` instead of `ivr_response.transfer_destination` for STAFF policy transfers~~ | HIGH | **Fixed in audit** |
| GAP-001 | ~~IVR timeout/no-input has no explicit recovery prompt~~ | MEDIUM | **Fixed — P1-005** |
| GAP-002 | ~~No IVR repeat menu key~~ | LOW | **Fixed — P1-007** |
| GAP-003 | ~~No SMS reply parsing (confirm/cancel by text reply)~~ | MEDIUM | **Fixed — P1-002** |
| GAP-004 | ~~No reschedule flow (IVR or admin)~~ | MEDIUM | **Fixed — P1-003/P1-004** |
| GAP-005 | ~~No reminder SMS~~ | MEDIUM | **Fixed — P1-001** |
| GAP-006 | ~~No IVR backend-unavailable fallback~~ | MEDIUM | **Fixed — P1-008** |
| GAP-007 | `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning from starlette 1.3.1 | LOW | Monitor — non-breaking |
| GAP-008 | CalendarIntegration staff_id not FK-validated at DB level | LOW | Open — AVS-TD-028 |
| GAP-009 | Phone numbers not masked in structured logs | MEDIUM | Open — Privacy risk |
| GAP-010 | ~~No DLQ alerting or metrics for failed async jobs~~ | MEDIUM | **Fixed — P1-011/P1-012** |
| GAP-011 | ~~`get_client`/`require_client`/`update_client`/`get_customer`/`require_customer`/`gdpr_delete_customer` (and pre-existing `get_staff`/`get_booking`) filter by `tenant_id` only, not `business_id`, despite routes accepting `business_id` in the URL — a tenant with multiple businesses can read/mutate/anonymize another business's client or customer data.~~ | CRITICAL | **Fixed — AVS-TD-029, PR #42** |
| GAP-012 | ~~Waitlist offer matching (`find_matching_waitlist_entries()`) has no row locking or idempotency guard; concurrent cancellations or an overlapping maintenance tick can double-offer the same waitlist entry.~~ | HIGH | **Fixed — AVS-TD-030, PR #45** |
| GAP-013 | `app/api/routes/twilio_voice.py:150`'s `VoiceSession` lookup doesn't validate `business_id`, only `session_id`; mitigated by mandatory Twilio signature validation. | LOW | Open — AVS-TD-031, see `docs/audits/pre-p3-readiness-audit.md` |
| GAP-014 | ~~Same pattern as GAP-011, found in two files that audit didn't cover: `require_working_hours`/`require_availability_exception` filtered by `tenant_id` only, despite their GET/DELETE routes accepting `business_id` in the URL.~~ | CRITICAL | **Fixed — AVS-TD-032** |

## Readiness Assessment

| Level | Status | Reason |
|-------|--------|--------|
| NOT_READY | ✅ Exceeds | All core flows demonstrable |
| PORTFOLIO_READY | ✅ Yes | Clean domain, tests, CI, real providers, honest limitations |
| MVP_DEMO_READY | ✅ Yes | Full local simulated call-to-booking-to-SMS-to-calendar works |
| PILOT_READY | ✅ Yes | Providers wired; BUG-001 fixed; IVR timeout/invalid-input/repeat/reschedule handled, admin reschedule API added, IVR degrades gracefully on DB/Redis outage instead of exposing raw errors, per-job-type queues, DLQ depth/failure-rate alerting, provider-level failure metrics, full lifecycle audit trail incl. admin override wired (P1-001 through P1-013 all done). GAP-011 (cross-business data exposure) and GAP-012 (waitlist double-offer race) — the two former pilot blockers — are both fixed. GAP-013 (low severity, mitigated by signature validation) remains open but does not block pilot traffic. See `docs/audits/pre-p3-readiness-audit.md`. |
| PRODUCTION_READY | ❌ No | Missing: owner metrics/CSV export (P2-013/P2-014), billing, monitoring dashboards, P3 operational extensions beyond admin override |

## Not Implemented (Expansion Backlog)

Audited 2026-06-17, updated 2026-06-22 after P1-001 through P1-013, P2-001
through P2-012, and P3-001/P3-002/P3-003/P3-004/P3-005/P3-009/P3-012. See
`docs/audits/p3-remaining-backlog-audit.md` for the full remaining-backlog
verification and a documentation-accuracy review (corrected six stale
`TECH_DEBT.md` rows that hadn't been flipped to Done when their underlying
features shipped, plus one flipped to In Progress to reflect partial-only
coverage).
52 P1–P4 items tracked; 33 fully implemented or covered, 4 partially, 15 not yet started.

**P1 — Must-have for pilot:**
- NOT_IMPLEMENTED: none.
- PARTIAL: none — audit log expansion (P1-013) is now fully done, including
  the admin-override portion (P3-012, see P3 section below).
- DONE: reminder SMS queued once per booking within `reminder_lead_minutes`
  of the appointment via the worker maintenance tick (P1-001), inbound SMS
  reply confirm/cancel parsing via `/webhooks/twilio/sms/{business_id}/inbound`
  acting on the customer's soonest upcoming booking, idempotent cancel
  (P1-002), IVR self-service cancel/reschedule of the caller's soonest
  upcoming booking via main-menu option 3 (P1-003), admin reschedule via
  `POST /businesses/{business_id}/bookings/{booking_id}/reschedule` (P1-004)
  — both reschedule paths share `reschedule_booking()` in
  `booking_service.py`, which cancels the old booking and creates a new one
  for the same service/staff at the new time (the calendar adapter only
  supports create/cancel, not updating an already-synced event's time), IVR
  no-input timeout handling with consecutive-miss termination (P1-005), IVR
  invalid-input retry counter with session termination after 5 keys
  (P1-006), IVR repeat-menu key `*` at every interactive step (P1-007), IVR
  voice webhook returns graceful "technical difficulties" TwiML instead of a
  raw 500/JSON error when the DB or Redis is unavailable mid-call, with no
  partial session/booking left behind (P1-008), per-job-type Redis queues via
  `queue_name_for_job_type()` so a backlog/outage in one integration (e.g.
  calendar sync) can't head-of-line block another (e.g. SMS) sharing a single
  FIFO list (P1-009), DLQ alerting via the new `worker_failed_queue_depth`
  Prometheus gauge (refreshed every maintenance tick) plus two Alertmanager
  rules in `observability/prometheus/rules/worker-alerts.yml`
  (`WorkerFailedQueueBacklog`, `WorkerJobFailureRate`) (P1-011), provider-level
  failure metrics (`sms_provider_requests_total`,
  `calendar_provider_requests_total`) instrumented at the actual
  `SmsProvider.send()`/calendar provider call sites — finer-grained than
  job-level since a job can retry against the provider multiple times
  (P1-012), `BOOKING_RESCHEDULED` audit entry on the new booking (`source`
  links back to the old booking id), `BOOKING_CONFIRMED` audit entry on
  SMS reply CONFIRM, and `BOOKING_OVERRIDE_CREATED`/`BOOKING_OVERRIDE_CANCELLED`
  audit entries on admin override actions (P3-012), on top of the existing
  create/cancel audit trail (P1-013).
- DONE (covered by MVP): exponential backoff (`calculate_retry_delay_seconds()`).

**P2 — High business impact:**
- NOT_IMPLEMENTED: owner metrics API, CSV export.
- DONE: CRM clients table — `Client` model (name/email/phone/notes), optionally
  linked 1:1 to a `Customer` via `customer_id`; CRUD at
  `/businesses/{business_id}/clients` (P2-001), bookings linked to clients —
  no new column needed since `Booking.customer_id` + `Client.customer_id`
  (already unique per business) is a complete path; `get_bookings_for_client()`
  in `client_service.py` (P2-002), IVR personalizes the main-menu greeting
  ("Welcome back, {name}!") for a caller phone matching an existing
  Customer/Client for the exact business+tenant (P2-003), client booking
  history exposed at `GET /businesses/{business_id}/clients/{client_id}/bookings`
  (P2-004), GDPR delete via `POST /businesses/{business_id}/customers/{customer_id}/gdpr-delete`
  — anonymizes PII on the `Customer` and any linked `Client` rather than
  hard-deleting (no `ON DELETE` clause on `Booking.customer_id`, and a hard
  delete would break the booking/audit trail); applies regardless of
  booking status (P2-005), preferred staff selection in the IVR — new
  `STAFF_SELECTION` step between service and slot selection, offered only
  when 2+ active staff have a configured staff-specific working-hours
  schedule (`get_available_slots()` matches `staff_id` strictly against
  that staff member's own hours with no business-level fallback, so an
  unscheduled staff member would always dead-end in "no slots"); 0 or 1
  schedulable staff auto-skips the step; caller can press 0 for "any
  available staff"; the pre-existing `VoiceSession.selected_staff_id`
  column is now actually populated and threaded through to slot search and
  `create_booking()` (P2-006), suggest last staff member — new
  `get_last_staff_booking()` looks up the caller's most recent past booking
  (matched by phone, same scoping as the P2-003 returning-caller greeting)
  with a `staff_id` set; if still active/schedulable, that staff member is
  reordered to the front of the staff-selection menu (always option "1")
  and called out by name; no history, or a no-longer-eligible last staff
  member, leaves the P2-006 menu unaffected (P2-007), multi-service
  appointment model — new additive `BookingLineItem` model/table
  (`booking_id`, `service_id`, `position`, `duration_minutes` snapshot)
  lets a booking carry an ordered list of services; `Booking.service_id`/
  `ends_at` keep their existing meaning (primary/first service), so every
  existing single-service code path (IVR, availability search, calendar
  sync) is completely unaffected; `add_booking_line_item()`/
  `list_booking_line_items()`/`get_booking_total_duration_minutes()` in
  `booking_service.py`; not yet wired into availability search or the IVR
  — that's P2-009 (P2-008), combined-duration availability — new
  `get_available_slots_for_total_duration()` sibling of
  `get_available_slots()` searches for a combined duration across
  multiple services (built from P2-008's `BookingLineItem` rows) instead
  of a single `service_id`'s `duration_minutes`; both share the same
  private slot-generation core, parameterized by duration, so the existing
  single-service function/signature/call sites (IVR, availability API) are
  unchanged; not yet wired into `create_booking()` or the IVR flow itself
  (P2-009), waitlist model — new `WaitlistEntry` model/table
  (`customer_id`, `service_id`, optional `staff_id` for a preferred staff
  member, `desired_date`, `status`: WAITING/OFFERED/CONFIRMED/EXPIRED/
  CANCELLED on a plain `String` column); `create_waitlist_entry()`/
  `list_waitlist_entries()`/`update_waitlist_entry_status()` in new
  `waitlist_service.py` (P2-010), offer waitlist
  after cancellation — `cancel_booking()` now calls new
  `find_matching_waitlist_entries()` (business/service/desired_date, plus
  staff: entries with no staff preference always match, entries wanting a
  specific staff member only match if that's the staff member who just
  freed up) and transitions only the oldest matching WAITING entry to
  OFFERED, recording the freed slot's staff on new `offered_for_staff_id`
  column (migration `p2012a2b3c4d5e`) and enqueuing a new `WAITLIST_OFFER`
  SMS notification (`NotificationPurpose` value on the existing `String`
  `purpose` column, no DDL change) via `enqueue_waitlist_offer()`; the rest
  stay WAITING (P2-011), waitlist timeout/escalation — new
  `expire_stale_waitlist_offers()` runs from `run_scheduled_maintenance()`,
  expires OFFERED entries idle longer than
  `settings.waitlist_offer_timeout_minutes` (default 60) and offers the
  next-oldest eligible WAITING entry in their place, matched against the
  expired entry's `offered_for_staff_id` (not its own `staff_id`
  preference, which can be NULL even when the freed slot belonged to a
  specific staff member) via the same
  `find_matching_waitlist_entries()`/`enqueue_waitlist_offer()` path
  (P2-012).

**P3 — Operational extensions:**
- NOT_IMPLEMENTED: deposits ADR, Stripe payment links, pending-payment
  booking state, calendar privacy rules, calendar conflict import ADR,
  integration reconciliation job, two-way calendar ADR.
- DONE: salon closures/holidays — business-wide closure exclusion and overlap
  validation already worked; added the missing API clarity (create
  endpoint docstring documents that a business-wide `staff_id=null`
  closure always wins over any staff-specific exception for the same
  date, and that a staff-specific exception never leaks into other staff
  members' or an "any available staff" search) and precedence/isolation
  tests the audit flagged as missing (P3-003); salon opening hours API — `POST /businesses/{business_id}/working-hours`
  previously hardcoded `staff_id=None`, so a real admin had no API path to
  configure a staff-specific schedule at all (only business-wide "salon"
  hours), even though `get_available_slots()` and P2-006's IVR
  staff-selection menu both depend on staff having their own `WorkingHours`
  rows; added an optional `staff_id` field, validated against the business
  the same way as other `staff_id`-accepting endpoints (P3-001); salon/staff
  hours intersection — `_get_available_slots_for_duration()` now intersects
  a staff member's specific hours against the salon's wide ones (a slot
  only counts if both are open; a wider staff window gets clipped to the
  salon's); the fallback (use the other side's hours when one side has
  *zero* `WorkingHours` rows configured at all) is symmetric and based on
  whether that side has any row on *any* day, not just the queried one —
  a side with a managed-but-partial schedule (e.g. salon or staff open
  Mon-Fri only) stays closed on an unconfigured day rather than silently
  inheriting the other side's hours that day; two asymmetric variants of
  this bug (staff-side, then salon-side) were each caught in cross-provider
  review and fixed pre-merge with dedicated regression tests; this also fixed
  `_schedulable_staff()` in the IVR (P2-006), which had wrongly excluded
  every such staff member from the selection menu — the demo seed (staff
  with no individual schedule) had silently made per-staff IVR selection
  dead before this fix (P3-002); one-off staff/business time blocks — `create_availability_exception()`
  now validates `staff_id` belongs to the business (404 otherwise) and
  rejects a new exception that conflicts with an existing one for the same
  (business_id, staff_id, date) scope: a full-day closure can't coexist with
  any other row for that scope/date, and two "special hours" rows can't have
  overlapping time windows (non-overlapping windows remain allowed — the
  existing lunch-block pattern); deliberately does not cross-check a
  staff-specific row against a business-wide row, since that precedence
  question belongs to P3-002/003 (P3-004); manual admin override workflow — `POST /businesses/{business_id}/bookings/override`
  and `POST /businesses/{business_id}/bookings/{booking_id}/override-cancel`,
  both admin-only with a required, non-blank `reason`, logging the new
  `AuditAction.BOOKING_OVERRIDE_CREATED`/`BOOKING_OVERRIDE_CANCELLED`
  (queryable separately from regular create/cancel); override-create does
  **not** bypass the DB-level `no_overlapping_staff_bookings` exclusion
  constraint for a genuine same-staff conflict — that remains a 409, a
  deliberate scope decision (P3-012); multilingual IVR prompt architecture —
  new `app/core/ivr_prompts.py` (`PromptKey` enum, locale-keyed `_PROMPTS`
  dict, `resolve_prompt()`/`format_option_list()`); every prompt/label in
  `ivr_service.py` now resolves through a single `_session_locale(session)`
  extension point; only `en` is populated (translation content is out of
  scope), but adding a real locale later requires zero step-handler changes
  (P3-009); recurring staff blocks — new `RecurringStaffBlock` model per
  ADR 0003, business-scoped CRUD with same-scope overlap validation,
  subtracted from generated slots as a third precedence step after
  `WorkingHours`/`AvailabilityException` in `_get_available_slots_for_duration()`,
  verified to stay correct when working hours change later instead of going
  stale (P3-005).

**P4 — SaaS model and scale:**
- NOT_IMPLEMENTED: phone provisioning, Stripe Billing model, plan limits
  enforcement, billing webhooks, plan-limit blocking, backward-compatibility
  checklist (P4-006 through P4-011).
- DONE: onboarding wizard API (P4-005) — duplicate/already covered by
  AVS-L004's `POST /api/v1/onboarding` (business+staff+services+hours setup
  in one call); the roadmap row was still listed `[ ]` until
  `docs/audits/p3-remaining-backlog-audit.md` found the duplicate coverage.
- PARTIAL: self-service salon onboarding (P4-004) — AVS-L004 covers the
  "setup business profile" half; true self-serve "signup" (a new owner
  provisioning their own tenant/admin account) is still manual, tenancy
  query audit (`test_product_tenant_isolation.py` exists; systematic
  checklist missing), product tenant guards (`require_business()` pattern exists;
  standardized dependency not abstracted), cross-tenant leakage tests (per-feature
  tests exist; per-route CI requirement missing).

## Rules for Updating This File

- Only list verified behavior (code + tests or justified no-test reason).
- Planned work belongs in `docs/appointment-saas-roadmap.md`.
- Gaps belong in `TECH_DEBT.md`.
