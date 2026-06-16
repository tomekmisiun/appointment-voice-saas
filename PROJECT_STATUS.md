# Project Status — Appointment Voice SaaS

Verified as of 2026-06-16. Updated during `audit/roadmap-reality-check`.

## Current Status

All MVP foundation epics (A–J) implemented. 613 tests pass. CI green.

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

## Known Limitations and Gaps

| ID | Gap | Severity | Status |
|----|-----|----------|--------|
| BUG-001 | ~~Twilio keypress route used `business.phone` instead of `ivr_response.transfer_destination` for STAFF policy transfers~~ | HIGH | **Fixed in audit** |
| GAP-001 | IVR timeout/no-input has no explicit recovery prompt (falls through to re-prompt) | MEDIUM | Open — see P1-005 |
| GAP-002 | No IVR repeat menu key (P1-007) | LOW | Open |
| GAP-003 | No SMS reply parsing (confirm/cancel by text reply) | MEDIUM | Open — P1-002 |
| GAP-004 | No reschedule flow (IVR or admin) | MEDIUM | Open — P1-003/P1-004 |
| GAP-005 | No reminder SMS | MEDIUM | Open — P1-001 |
| GAP-006 | No IVR backend-unavailable fallback | MEDIUM | Open — P1-008 |
| GAP-007 | `HTTP_422_UNPROCESSABLE_ENTITY` deprecation warning from starlette 1.3.1 | LOW | Monitor — non-breaking |
| GAP-008 | CalendarIntegration staff_id not FK-validated at DB level | LOW | Open — AVS-TD-028 |
| GAP-009 | Phone numbers not masked in structured logs | MEDIUM | Open — Privacy risk |
| GAP-010 | No DLQ alerting or metrics for failed async jobs | MEDIUM | Open — P1-011/P1-012 |

## Readiness Assessment

| Level | Status | Reason |
|-------|--------|--------|
| NOT_READY | ✅ Exceeds | All core flows demonstrable |
| PORTFOLIO_READY | ✅ Yes | Clean domain, tests, CI, real providers, honest limitations |
| MVP_DEMO_READY | ✅ Yes | Full local simulated call-to-booking-to-SMS-to-calendar works |
| PILOT_READY | ⚠️ Conditional | Providers wired; BUG-001 fixed; but P1 gaps (no retry alerting, no reschedule, no timeout fallback) remain |
| PRODUCTION_READY | ❌ No | Missing: reminder SMS, reschedule, IVR error recovery, DLQ alerting, CRM, billing, monitoring dashboards |

## Not Implemented (Expansion Backlog)

P1: Reminder SMS, SMS reply handling, reschedule, IVR timeout/invalid-input fallback,
backend-unavailable handler, DLQ alerting, monitoring metrics.

P2: CRM clients table, returning caller recognition, multi-service bookings, waitlist,
preferred staff selection, owner metrics API, GDPR delete.

P3: Salon vs staff hours intersection, staff time blocks, deposits/payments,
multilingual IVR, calendar conflict import, admin override workflow.

P4: SaaS onboarding, phone provisioning, Stripe Billing, plan limits, multi-tenant
product audit.

## Rules for Updating This File

- Only list verified behavior (code + tests or justified no-test reason).
- Planned work belongs in `docs/appointment-saas-roadmap.md`.
- Gaps belong in `TECH_DEBT.md`.
