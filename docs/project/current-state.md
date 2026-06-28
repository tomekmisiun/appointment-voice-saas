# VoxSlot — Current State

Last updated: 2026-06-28 (documentation audit; P4-001 phone-role separation already present; migration head documented as `p4001a2b3c4d5e` from repository state).

---

## Summary

VoxSlot is a multi-tenant appointment SaaS with an IVR voice-booking flow. The backend is feature-complete for the core booking domain. The frontend covers auth, booking management, and staff views. TELEPHONY-T9 (phone-number-based IVR routing) was forward-ported to `main` as P4-001; remaining telephony items (T1–T8, BusinessPhoneNumber model) exist only in the backup snapshot branch.

---

## Architecture

| Layer | Technology |
|---|---|
| Backend | FastAPI 0.x, Python ≥ 3.13, SQLAlchemy 2.0, Alembic |
| Database | PostgreSQL 17 (Railway plugin in production, Docker in local) |
| Queue / cache | Redis 7 (Railway plugin in production, Docker in local) |
| Workers | Polling Redis LIST, 5 job types + maintenance tick |
| Frontend | Next.js 16 (App Router), TypeScript, pnpm, Tailwind CSS v4 |
| Infrastructure | Railway (3 services: api, worker, frontend) |
| Local dev | Docker Compose (api, worker, db, test_db, redis, minio) |
| Object storage | S3-compatible (Minio locally, S3 in production via presigned URL) |

### Multi-tenancy

Every product table carries `tenant_id` as a foreign key. Tenant isolation is validated per-request. Business-level scoping is enforced via `require_business()` and per-service `tenant_id` filters. A systematic per-route isolation guard (P4-001/002/003) is not yet abstracted into CI enforcement.

### Auth

- JWT access tokens (30-minute TTL) + refresh tokens (7-day TTL)
- `token_version` column on `User` for token invalidation
- Demo user: `is_demo_user` flag; enforced read-only via `require_non_demo_user` dependency on all mutating endpoints

### Alembic migrations

43 migrations, single head: `p4001a2b3c4d5e`. Chain is clean (verified 2026-06-27; head updated by P4-001).

### Domain models

User, Tenant, Business, BusinessMembership, Staff, Service, WorkingHours, RecurringStaffBlock, AvailabilityException, Booking, BookingLineItem, BookingPayment, Customer, Client, NotificationOutbox, AuditLog, VoiceSession, UploadedFile, CalendarIntegration, WaitlistEntry, OwnerLead.

---

## Working Flows

### Signup / Login
- `POST /api/v1/signup` — creates Tenant + first admin User in one call
- `POST /api/v1/auth/register` — user registration (gated by `registration_enabled` flag)
- `POST /api/v1/auth/token` — JWT login
- `POST /api/v1/auth/token/refresh` — token refresh
- Rate limited; token invalidation via `token_version`

### Demo
- `POST /api/v1/auth/demo` — creates or returns a demo user session
- Demo user has read-only access enforced by `DemoReadOnlyMiddleware` and
  `require_non_demo_user` on mutating endpoints
- Frontend route `/demo` exists and serves the demo experience
- `app/seed_demo_data.py` seeds deterministic demo data through `make seed-demo`

### IVR / Voice Booking
- Twilio webhook: `POST /api/v1/webhooks/twilio/voice` — routes by `To=` field matched against `businesses.phone`; keypress action URL is `/api/v1/webhooks/twilio/voice/{session_id}` (no `business_id` in any path)
- Twilio signature validation enforced on all webhook handlers
- Full IVR flow: incoming call → main menu → service selection → staff selection → slot proposal → booking confirmation
- Handles: no-input (3 retries), invalid input (5 cumulative), repeat menu (`*`), transfer to staff, backend-unavailable fallback
- IVR simulator endpoint: `POST /api/v1/ivr/simulate/...` (backend only; no frontend UI for simulator)
- SMS reply handling: `C`/`CONFIRM`/`YES` confirms; `X`/`CANCEL`/`NO` cancels the caller's next upcoming booking
- Reschedule via IVR: option 3 on main menu

### Booking
- Create, cancel, reschedule (API + IVR)
- Double-booking prevented at DB level via `btree_gist EXCLUDE` constraint
- Admin override: `POST /businesses/{business_id}/bookings/override` (with mandatory reason, audit logged)
- Pending payment hold: `BookingStatus.PENDING_PAYMENT` reserves slot; hold expires via worker

### SMS Notifications
- Confirmation SMS after booking (customer + business)
- Cancellation SMS
- Reminder SMS (1440 minutes before appointment, hardcoded in `settings.reminder_lead_minutes`)
- Waitlist offer SMS on cancellation
- Providers: `FakeSmsProvider` (dev/test), `TwilioSmsProvider` (production), `NullSmsProvider`
- All messages are EN-only hardcoded f-strings; no per-business SMS templates

### Calendar
- Fake calendar provider for local dev/test
- CalendarIntegration model exists; no active frontend for connecting real providers
- Outbox-backed calendar sync with retry/DLQ

### Workers
5 job types processed by polling worker:
1. `SEND_SMS` — notification outbox processing
2. `SYNC_CALENDAR` — calendar event sync
3. `PROCESS_WAITLIST_OFFER` — waitlist offers
4. `EXPIRE_VOICE_SESSION` — IVR session cleanup
5. `MAINTENANCE` — reminder scheduling, payment hold expiry, waitlist timeout/escalation, integration reconciliation

---

## Backend Status

### Done (API complete with tests)
- Auth: register, login, refresh, demo, GDPR delete
- Self-service signup (`POST /api/v1/signup`)
- Business CRUD
- Staff CRUD
- Service CRUD (incl. deposit fields)
- WorkingHours CRUD (business-wide and staff-specific)
- RecurringStaffBlock CRUD
- AvailabilityException CRUD
- Availability API (slot generation with intersection of salon+staff hours, recurring blocks, exceptions)
- Booking: create, list, read, cancel, reschedule, admin override, pending-payment hold
- Customer: create, GDPR anonymize
- Client (CRM): CRUD
- Client booking history API
- Waitlist: create, list, update status, offer on cancellation, timeout escalation
- NotificationOutbox: create, worker processing, retry/DLQ
- AuditLog: 18 action types, queryable
- Rate limiting: Redis-based on auth + webhooks
- File uploads: S3/Minio presigned URL
- IVR full flow (Twilio + simulator)
- Owner leads (`POST /api/v1/owner-leads`)
- Onboarding wizard (`POST /api/v1/onboarding`)
- Platform admin: tenant provision, user management

### Partial
- `BusinessMembership` — model and migration exist (`sac003`); RBAC check is **not** wired into the authorization layer. `User.role` is used for auth decisions; `BusinessMembership.role` is stored but ignored in runtime checks. (SAC-005 not completed)
- Customer: GDPR delete exists; `GET/LIST/PATCH` customer endpoints do not exist
- `CalendarIntegration`: model and fake provider exist; no real OAuth flow; no frontend
- Multi-service booking: `BookingLineItem` model and combined-duration availability exist; not wired into the IVR flow or booking creation API

### Not Started (on `main`)
- `BusinessPhoneNumber` model
- `telephony_status` column on Business
- `TelephonyStatusCard` frontend component
- `DemoSmsProvider`
- SMS templates (per-business, user-editable)
- Booking management public link (HMAC token, public cancel/reschedule endpoint)
- Stripe payment links (P3-007, deliberately deferred)
- Billing/subscriptions (P4-007 through P4-010)
- Per-business IVR prompt customization (P4-012, defined but not implemented)
- Owner metrics API (P2-013)
- CSV export (P2-014)

---

## Frontend Status

### Routes (21 pages compiled, Next.js 16 + Turbopack)
| Route | Status |
|---|---|
| `/` | Landing page — links to `/register`, `/about`; no CTA to `/demo` |
| `/register` | Registration form |
| `/login` | Login form |
| `/demo` | Demo experience page (exists) |
| `/dashboard` | Owner dashboard skeleton |
| `/dashboard/bookings` | Booking list + cancel/reschedule dialogs |
| `/dashboard/staff` | Staff list |

### Missing Frontend Screens
- Services management
- Working hours configuration
- Recurring staff blocks
- Availability exceptions
- IVR simulator UI
- SMS template editor
- Telephony configuration (TelephonyStatusCard)
- Client/CRM browser
- Booking management (public, customer-facing)
- Owner metrics / analytics dashboard
- Calendar integration setup

### API Types
`openapi.json` and `schema.gen.ts` updated 2026-06-27 — frontend API types are current.

---

## Infrastructure Status

### Railway (Production)
The latest repository-local evidence is the 2026-06-27 audit snapshot. Live
Railway status was not rechecked during the 2026-06-28 documentation audit.

| Service | Last known status from 2026-06-27 audit |
|---|---|
| Frontend (`voxslot.up.railway.app`) | HTTP 200 — LIVE |
| API (`api-production-52a1.up.railway.app`) | **502 Bad Gateway — DOWN** |
| Worker | Status unknown (depends on API startup) |
| Postgres plugin | Provisioned |
| Redis plugin | Provisioned |

**Do not rely on production until Railway health is checked.** Root cause was
not determined in the historical audit; Railway dashboard investigation is
required if the issue still reproduces.

### CI Pipeline
CI includes pre-commit, policy guards, secret scanning, backend tests with
coverage, load smoke, Docker build/security scan, frontend validation, public
demo contract tests, and deploy on `main`.
- Deploy runs only after all CI jobs pass (green gate enforced)
- Alembic `upgrade head` runs as a pre-deploy step on Railway
- Branch: `ci/railway-auto-deploy` merged; current `main` has Railway auto-deploy wired

### Local Development
`docker compose up` starts: api, worker, db, test_db, redis, minio.
Full IVR simulation available locally without Twilio credentials.

---

## Test Results (2026-06-27)

| Suite | Result |
|---|---|
| Policy guards (`make policy-guards`) | PASS in 2026-06-27 audit |
| Alembic head check | PASS (1 head: `p4001a2b3c4d5e`) |
| Frontend type-check (`tsc`) | PASS |
| Frontend lint (ESLint) | PASS |
| Frontend build (Next.js) | PASS (21 routes) |
| Frontend tests (Vitest) | PASS 164/164 |
| Python ruff | PASS |
| Backend pytest | NOT RUN in 2026-06-27 audit (requires Docker dependencies) |

Coverage policy is 85% in `pyproject.toml` and `Makefile`. Do not rely on a
static test count without rerunning the suite.

---

## Known Limitations

1. Production API is down (502) — requires Railway dashboard investigation
2. `BusinessMembership.role` is not used in runtime authorization (SAC-005 incomplete)
3. SMS messages are hardcoded EN-only; no per-business language or template support
4. No public booking management link — customers cannot cancel/reschedule without calling or contacting business
5. Telephony T1–T8 (`BusinessPhoneNumber` model, telephony_status column, operator API) not on `main`; exists only in `backup/mixed-work-before-recovery-2026-06-26` snapshot. T9 (phone-number IVR routing) was forward-ported as P4-001 and is fully on `main`.
6. Landing page (`/`) does not link to `/demo` — reduces demo discoverability
7. `staff_invitations` table (SAC-009) exists in the backup snapshot; if it was ever applied to production DB, a fresh DB will not have it (potential prod/fresh-DB divergence — investigate Railway DB state)
8. Node version: local dev may use Node 26; `package.json` engines specifies `^22.13.0`
9. `CalendarIntegration` model exists but no real OAuth flow; frontend calendar setup screen does not exist

---

## Readiness Assessment

| Target | Status | Blocking Issues |
|---|---|---|
| Local development | READY | None |
| Portfolio demo (local) | READY | None |
| Portfolio demo (production) | NOT READY | API prod down (502) + no CTA on landing page |
| Public demo (production) | NOT READY | Same as above |
| Pilot (real businesses) | NOT READY | SMS templates, booking management link, API down |
| Production SaaS | NOT READY | All pilot blockers + billing, subscriptions, phone provisioning |
