# Project Status — Appointment Voice SaaS

Verified as of 2026-06-17. Updated during `audit/backlog-reality-check`.

## Current Status

All MVP foundation epics (A–K) and full Epic L (L001–L004, owner acquisition + onboarding) implemented. 695 tests pass. CI green.

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

## Readiness Assessment

| Level | Status | Reason |
|-------|--------|--------|
| NOT_READY | ✅ Exceeds | All core flows demonstrable |
| PORTFOLIO_READY | ✅ Yes | Clean domain, tests, CI, real providers, honest limitations |
| MVP_DEMO_READY | ✅ Yes | Full local simulated call-to-booking-to-SMS-to-calendar works |
| PILOT_READY | ✅ Yes | Providers wired; BUG-001 fixed; IVR timeout/invalid-input/repeat/reschedule handled, admin reschedule API added, IVR degrades gracefully on DB/Redis outage instead of exposing raw errors, per-job-type queues, DLQ depth/failure-rate alerting, provider-level failure metrics, create/cancel/reschedule/SMS-confirm audit trail wired (P1-001 through P1-009, P1-011 through P1-013); only the admin-override portion of audit logging (blocked on P3-012, which doesn't exist yet) remains open |
| PRODUCTION_READY | ❌ No | Missing: admin override audit trail (needs P3-012 first), CRM, billing, monitoring dashboards |

## Not Implemented (Expansion Backlog)

Audited 2026-06-17, updated 2026-06-18 after P1-001 through P1-013 (see below)
and P2-001 through P2-007.
50 P1–P4 items checked; 18 fully implemented, 4 partially, 2 already covered by
MVP infrastructure.

**P1 — Must-have for pilot:**
- NOT_IMPLEMENTED: none (all remaining P1 items are partial — see below).
- PARTIAL: audit log expansion (create/cancel/reschedule/SMS-confirm logged;
  admin-override audit pending P3-012, which doesn't exist yet).
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
  links back to the old booking id) and `BOOKING_CONFIRMED` audit entry on
  SMS reply CONFIRM, on top of the existing create/cancel audit trail
  (P1-013).
- DONE (covered by MVP): exponential backoff (`calculate_retry_delay_seconds()`).

**P2 — High business impact:**
- NOT_IMPLEMENTED: multi-service appointments, combined-duration
  availability, waitlist model, waitlist-on-cancellation offer, waitlist
  timeout/escalation, owner metrics API, CSV export.
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
  member, leaves the P2-006 menu unaffected (P2-007).

**P3 — Operational extensions:**
- NOT_IMPLEMENTED: salon/staff hours intersection, recurring staff blocks,
  deposits ADR, Stripe payment links, pending-payment booking state,
  multilingual IVR, calendar privacy rules, calendar conflict import ADR,
  admin override workflow, integration reconciliation job, two-way calendar ADR.
- PARTIAL: salon opening hours (`WorkingHours` nullable staff_id exists;
  availability intersection missing), salon closures/staff time blocks
  (`AvailabilityException` nullable staff_id exists; API validation and tests missing).

**P4 — SaaS model and scale:**
- NOT_IMPLEMENTED: self-service onboarding, onboarding wizard, phone provisioning,
  Stripe Billing model, plan limits enforcement, billing webhooks, plan-limit
  blocking, backward-compatibility checklist.
- PARTIAL: tenancy query audit (`test_product_tenant_isolation.py` exists; systematic
  checklist missing), product tenant guards (`require_business()` pattern exists;
  standardized dependency not abstracted), cross-tenant leakage tests (per-feature
  tests exist; per-route CI requirement missing).

## Rules for Updating This File

- Only list verified behavior (code + tests or justified no-test reason).
- Planned work belongs in `docs/appointment-saas-roadmap.md`.
- Gaps belong in `TECH_DEBT.md`.
