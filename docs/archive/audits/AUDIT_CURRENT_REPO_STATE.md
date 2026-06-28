> [!WARNING]
> This document is archived and does not describe the current state of the project.
> See the current documentation: [`../../CURRENT_STATE.md`](../../project/current-state.md) and [`../../README.md`](../../README.md).

# Audit: Current Repository State

**Date:** 2026-06-27
**Commit SHA:** `8f8912b` (branch `main`, clean working tree, up to date with `origin/main`)
**Auditor:** Research agent (multi-step automated audit)
**Methodology:** Static code inspection + file system search + command execution (no docker compose; backend pytest not run). All findings are from direct source code inspection or command output unless marked UNVERIFIED.

---

## 1. Git State

### Branch and working tree

```
Branch:          main
Working tree:    clean (no uncommitted changes)
Upstream:        origin/main, 0 commits ahead, 0 behind
```

### Recent commits (last 9 on main)

```
8f8912b  fix(railway): use named config files and Nixpacks for frontend
82e6b19  ...
de74cd3  ...
66185a0  ...
3ad2853  ...
ebc4375  ...
9083d01  ...
a150d5c  ...
249fc52  ...
```

All 9 recent commits are Railway/CI deployment fixes. No feature commits since the `ci/railway-auto-deploy` branch was merged.

### Remote branches

- `origin/main` — primary branch
- `origin/feat/public-demo-readonly` — remote branch; merged via PR #82 and PR #83; content is on `main`
- `origin/fix/demo-migration-head` — likely stale after `de74cd3`
- `origin/ci/railway-auto-deploy` — merged

### Backup snapshot

- `backup/mixed-work-before-recovery-2026-06-26` — documented in `docs/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md`; this branch is NOT present on `origin`; its commits contain telephony (T1–T9), SAC-005/006/007/008b/009, SMS template stubs, and Railway config work that was never cleanly extracted to `main`

### Tags

None.

### Alembic migrations

43 migration files. Single head: `demo_user_flag_a1b2c3d4`. Chain is clean — no branching, no multiple heads.

---

## 2. Architecture

### Backend stack

| Component | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic (43 revisions, 1 head) |
| Database | PostgreSQL 17 |
| Queue / cache | Redis 7 (polling LIST; 5 job types + maintenance tick) |
| Auth | JWT (access 30min + refresh 7 days) + `token_version` invalidation |
| Tenancy | `tenant_id` FK on every product table; per-request validation |
| Object storage | S3/Minio (presigned URL) |
| Rate limiting | Redis-based (auth endpoints + Twilio webhooks) |

### Frontend stack

| Component | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| Language | TypeScript |
| Package manager | pnpm |
| Styling | Tailwind CSS v4 |
| Tests | Vitest (164 passing) |
| API types | `openapi.json` + `schema.gen.ts` (updated 2026-06-27) |

### Infrastructure

| Component | Platform |
|---|---|
| API | Railway service |
| Worker | Railway service |
| Frontend | Railway service |
| Database | Railway Postgres plugin |
| Cache | Railway Redis plugin |
| CI | GitHub Actions (8 jobs) |
| Local dev | Docker Compose (api, worker, db, test_db, redis, minio) |

### Domain models (on main)

User, Tenant, Business, BusinessMembership, Staff, Service, WorkingHours, RecurringStaffBlock, AvailabilityException, Booking, BookingLineItem, BookingPayment, Customer, Client, NotificationOutbox, AuditLog, VoiceSession, UploadedFile, CalendarIntegration, WaitlistEntry, OwnerLead.

**Not on main (in backup snapshot only):** BusinessPhoneNumber, staff_invitations (SAC-009).
**Not on main (never implemented):** SmsTemplate.

---

## 3. Feature Inventory

### Core platform

| Feature | Status | Evidence |
|---|---|---|
| Multi-tenant architecture | DONE | `tenant_id` FK on all tables; per-request validation |
| JWT auth (access + refresh) | DONE | `app/api/routes/auth.py:73,109` |
| Token invalidation (`token_version`) | DONE | `User.token_version`; checked on every protected request |
| User registration | DONE | `app/api/routes/auth.py:49` |
| Self-service tenant signup | DONE | `POST /api/v1/signup`; `app/api/routes/signup.py` |
| Demo user (read-only) | DONE | `app/api/routes/auth.py:159`; `is_demo_user` flag; `require_non_demo_user` on 50+ endpoints |
| Rate limiting | DONE | Redis-based on auth + webhooks |
| Audit log (18 action types) | DONE | `app/models/audit_log.py`; 18 `AuditAction` values |
| File uploads (S3/Minio) | DONE | `app/api/routes/uploads.py`; presigned URL |

### Business domain

| Feature | Status | Evidence |
|---|---|---|
| Business CRUD | DONE | `app/api/routes/businesses.py` |
| Staff CRUD | DONE | `app/api/routes/staff.py` |
| Service CRUD (with deposit fields) | DONE | `app/api/routes/services.py` |
| WorkingHours CRUD (business-wide + staff-specific) | DONE | `app/api/routes/working_hours.py`; `staff_id` optional on create |
| RecurringStaffBlock CRUD | DONE | `app/api/routes/recurring_staff_blocks.py` |
| AvailabilityException CRUD | DONE | `app/api/routes/availability_exceptions.py` |
| Availability slot generation | DONE | Intersects salon hours + staff hours + recurring blocks + exceptions |
| Booking creation (with double-booking prevention) | DONE | DB-level `btree_gist EXCLUDE` constraint |
| Booking cancel | DONE | `app/services/booking_service.py:cancel_booking()` |
| Booking reschedule (admin) | DONE | `POST /businesses/{bid}/bookings/{id}/reschedule` |
| Admin override (with reason + audit) | DONE | `POST /businesses/{bid}/bookings/override` |
| Pending payment hold | DONE | `BookingStatus.PENDING_PAYMENT`; hold expiry via worker |
| Multi-service booking model | DONE (backend only) | `BookingLineItem`; not wired into IVR or create API |
| Customer CRM (Client model) | DONE (backend only) | `app/models/client.py`; no frontend screen |
| Customer GDPR anonymize | DONE | `POST /businesses/{bid}/customers/{cid}/gdpr-delete` |
| Waitlist (create, offer, escalate) | DONE | `app/services/waitlist_service.py` |
| Calendar adapter (fake provider) | DONE | `app/services/calendar_service.py`; outbox-backed |
| Calendar adapter (real OAuth) | NOT STARTED | `CalendarIntegration` model exists; no OAuth flow |
| BusinessMembership model | DONE (model only) | Migration `sac003`; model at `app/models/business_membership.py` |
| BusinessMembership RBAC enforcement | NOT DONE | `BusinessMembership.role` not used in auth decisions |
| BusinessPhoneNumber model | NOT STARTED | Not on main; in backup snapshot only |
| telephony_status on Business | NOT STARTED | Not on main; in backup snapshot only |

### IVR / Telephony

| Feature | Status | Evidence |
|---|---|---|
| IVR full flow (simulated) | DONE | `app/services/ivr_service.py`; full menu/service/slot/confirm flow |
| Twilio webhook adapter | DONE | `app/services/twilio_voice_adapter.py` |
| Twilio signature validation | DONE | `app/api/dependencies/twilio.py` |
| IVR no-input / invalid-input handling | DONE | `VoiceSession.no_input_count`, `invalid_key_count` |
| IVR repeat menu (`*`) | DONE | Every interactive step |
| IVR staff selection | DONE | `STAFF_SELECTION` step; skipped when 0 or 1 schedulable staff |
| IVR returning caller greeting | DONE | `app/services/ivr_service.py:start_session()` |
| IVR backend-unavailable fallback | DONE | Graceful TwiML on `OperationalError`/`RedisError` |
| IVR reschedule (caller option 3) | DONE | `docs/specs/ivr-reschedule.md` |
| IVR simulator endpoint | DONE (backend) | `app/api/routes/ivr.py`; no frontend UI |
| IVR multilingual prompt architecture | DONE | `app/core/ivr_prompts.py`; EN only populated |
| Phone-number-based IVR routing | NOT STARTED | Current: `business_id` in webhook URL |
| DemoSmsProvider | NOT STARTED | Not on main |

### SMS Notifications

| Feature | Status | Evidence |
|---|---|---|
| Booking confirmation SMS | DONE | `app/services/notification_service.py:enqueue_booking_confirmation()` |
| Booking cancellation SMS | DONE | `enqueue_booking_cancellation()` |
| Reminder SMS (1440min before) | DONE | Worker maintenance tick; `settings.reminder_lead_minutes` hardcoded default |
| Waitlist offer SMS | DONE | `enqueue_waitlist_offer()` |
| SMS reply handling (C/X) | DONE | `POST /webhooks/twilio/sms/{business_id}/inbound` |
| SMS retry / DLQ | DONE | Exponential backoff; DLQ metric |
| Per-business SMS templates | NOT STARTED | No `SmsTemplate` model anywhere |
| SMS localization (PL/EN) | NOT STARTED | EN-only hardcoded f-strings |
| Booking management link in SMS | NOT STARTED | No token generation; no public endpoint |
| FakeSmsProvider / NullSmsProvider | DONE | `app/services/sms_providers.py` |
| TwilioSmsProvider | DONE | `app/services/twilio_sms.py` |
| DemoSmsProvider | NOT STARTED | Not on main |

### Frontend

| Route | Status |
|---|---|
| `/` (landing page) | DONE — no /demo CTA |
| `/register` | DONE |
| `/login` | DONE |
| `/demo` | DONE |
| `/dashboard` | DONE (skeleton) |
| `/dashboard/bookings` | DONE (list + cancel/reschedule dialogs) |
| `/dashboard/staff` | DONE |
| Services screen | MISSING |
| Working hours screen | MISSING |
| Recurring staff blocks screen | MISSING |
| Availability exceptions screen | MISSING |
| IVR simulator UI | MISSING |
| SMS template editor | MISSING |
| Telephony status card | MISSING |
| Client/CRM browser | MISSING |
| Booking management (public) | MISSING |
| Owner metrics / analytics | MISSING |

---

## 4. Demo Audit

### Demo feature status

- `POST /auth/demo` — creates or returns demo user; issues JWT with `is_demo_user=true`
- `require_non_demo_user` dependency applied to 50+ mutating endpoints (verified: services, staff, bookings, working hours, etc.)
- `/app/demo/page.tsx` — frontend demo page exists
- `scripts/seed_demo_data.py` — seeds deterministic demo business, staff, services, hours, fake providers

### Demo gaps

- Landing page (`/`) has no CTA to `/demo` — customers/evaluators cannot find the demo from the homepage
- No demo banner in the dashboard UI indicating demo mode (OPTIONAL improvement)
- `DemoSmsProvider` not implemented — demo mode uses `FakeSmsProvider` or `NullSmsProvider`

### Mutation protection (sample)

All write endpoints that require `require_non_demo_user` return 403 if called with a demo JWT. This was implemented via PR #82 (`feat/public-demo-readonly`).

---

## 5. Telephony Audit (T1–T9)

| Item | Description | Status | Notes |
|---|---|---|---|
| T1 | `telephony_status` column on `Business` | NOT_STARTED | In backup snapshot only |
| T2 | `BusinessPhoneNumber` model + migration | NOT_STARTED | In backup snapshot only |
| T3 | Composite FK isolation for phone numbers | NOT_STARTED | Depends on T2 |
| T4 | Seed demo phone number in seed script | NOT_STARTED | Depends on T2 |
| T5 | Operator API (assign phone to business) | NOT_STARTED | Depends on T2, T3 |
| T6 | `TelephonyStatusCard` frontend component | NOT_STARTED | Depends on T5 |
| T7 | `DemoSmsProvider` | NOT_STARTED | Independent of T1–T6 |
| T8 | Booking source marker for demo IVR bookings | PARTIAL | `IVR` source exists; no `demo` marker |
| T9 | Phone-number-based IVR webhook routing | NOT_STARTED | Current: `business_id` in URL |

**Summary:** The entire telephony block (T1–T9) is not on `main`. It exists in the backup snapshot branch (`backup/mixed-work-before-recovery-2026-06-26`) as part of the contaminated `1ba87f5` commit and cannot be merged directly. Each item must be extracted onto a clean branch from the current `main` head.

---

## 6. SMS and Booking Management Audit

### SMS implementation state

- All messages are hardcoded EN-only Python f-strings in service files
- Message content: booking time, service name, staff name, business name
- Reminder lead time: `settings.reminder_lead_minutes`, default 1440 (24h before appointment), hardcoded default
- No `SmsTemplate` model in any migration or model file on `main`
- No `business.language` field

### Booking management link

- No `token_hash` or equivalent column on `Booking` model
- No public (unauthenticated) cancel or reschedule endpoint
- Confirmation SMS does not include a management link
- Customers can only manage bookings by calling back (IVR option 3) or contacting the business directly

### Decisions required before SMS template implementation

1. Locale field: `business.language` (ISO 639-1) or reuse existing metadata?
2. Template format: f-string placeholders, Handlebars, or custom DSL? (Handlebars adds a dependency; custom DSL requires a parser; f-string keys are simplest)
3. Placeholder validation strategy (prevent broken templates from causing SMS failures)

---

## 7. Test Results (2026-06-27)

| Suite | Command | Result |
|---|---|---|
| Policy guards | `make policy-guards` | PASS (exit 0) |
| Alembic head check | `alembic heads` | PASS — 1 head: `demo_user_flag_a1b2c3d4` |
| Frontend type-check | `pnpm tsc --noEmit` | PASS (exit 0) |
| Frontend lint | `pnpm eslint` | PASS (exit 0) |
| Frontend build | `pnpm build` | PASS (exit 0) — 21 routes, Next.js 16 + Turbopack |
| Frontend tests | `pnpm test` | PASS 164/164 (exit 0) |
| Python ruff | `ruff check .` | PASS (exit 0) |
| Backend pytest | `pytest` (requires docker compose) | NOT RUN in this audit |

### Historical backend test baseline (last known, pre-recovery)

- Test count: 900+ collected
- Pass rate: 100% (last green CI run)
- Coverage: ≥ 85% (floor enforced in CI)

---

## 8. Production Smoke Test (2026-06-27)

| Endpoint | URL | Result |
|---|---|---|
| API liveness | `https://api-production-52a1.up.railway.app/health/live` | **502 Bad Gateway** |
| Frontend | `https://voxslot.up.railway.app` | **HTTP 200 — LIVE** |
| Demo endpoint | `POST https://api-production-52a1.up.railway.app/auth/demo` | **502 Bad Gateway** |

**Production API is DOWN.** Frontend is serving. The Railway worker service status is unknown (likely also down if it depends on API startup or shared configuration).

Root cause: not determined in audit. Candidates: OOM kill, crash loop on startup, failed migration, missing environment variable. Requires Railway dashboard investigation.

---

## 9. SAC-00x Feature Audit (Staff Access and Calendar)

Based on `docs/specs/staff-access-and-calendar.md` and `docs/archive/superseded/staff-access-calendar-roadmap.md`:

| ID | Description | Status on main | Notes |
|---|---|---|---|
| SAC-001 | Data preflight / migration safety check | DONE | Pre-SAC-003 data preflight runbook exists |
| SAC-002 | Membership migration runbook | DONE | `docs/specs/sac-002-membership-migration-runbook.md` |
| SAC-003 | `business_memberships` table | DONE | Migration `sac003a2b3c4d5e6` on main |
| SAC-004 | Backfill existing users to memberships | DONE | Migration includes backfill |
| SAC-005 | Authorization context uses `BusinessMembership.role` | NOT DONE | `BusinessMembership.role` stored but not used in auth |
| SAC-006 | Staff profile lifecycle | NOT ON MAIN | Clean commit `a7bf6a1` in backup snapshot |
| SAC-007 | Staff service assignments | NOT ON MAIN | In backup snapshot (`1ba87f5`) |
| SAC-008b | Composite FKs on staff/service | NOT ON MAIN | In backup snapshot |
| SAC-009 | Staff invitations | NOT ON MAIN | In backup snapshot |
| SAC-010+ | Staff calendar, ICS import, Google OAuth | NOT STARTED | Planned in spec; no code |

---

## 10. Comparison with Planned Feature Branches

### `feat/public-demo-readonly`

- **Planned scope:** `is_demo_user` flag, `require_non_demo_user` on all mutating endpoints, `POST /auth/demo`, frontend `/demo` page, seed script
- **Status: LARGELY DONE** — all of the above is on `main` via PR #82 (`a6dd75a`) and PR #83 (`f818740`)
- **Remaining:** CTA on landing page (`/`) → `/demo` (estimated < 30 minutes). Optional: demo banner in dashboard UI.
- **Branch status:** `origin/feat/public-demo-readonly` still exists remotely but its content is on `main`. No further work needed on this branch.

### `feat/sms-template-management`

- **Planned scope:** `SmsTemplate` model, per-business templates, CRUD API, frontend editor
- **Status: NOT STARTED** — no code in any branch or commit in the repository
- **Blockers before implementation:**
  1. Decide locale approach (`business.language` field + EN/PL strings)
  2. Decide template format (f-string keys recommended for simplicity)
  3. Implement SMS localization first (shared infrastructure)
  4. Implement `SmsTemplate` model + migration
  5. Backend CRUD + placeholder validation
  6. Frontend editor screen
- **Ordering note:** should follow telephony (T1/T2) in case `telephony_status` influences template routing logic; can be done in parallel with `feat/public-booking-management-link`

### `feat/public-booking-management-link`

- **Planned scope:** HMAC token per booking, public cancel/reschedule endpoints, SMS link in confirmation
- **Status: NOT STARTED** — no code in any branch or commit in the repository
- **Implementation path:**
  1. Add `token_hash` nullable column to `Booking` (Alembic migration)
  2. Generate HMAC token at booking creation; store hash; send link in SMS
  3. `POST /booking/{token}/cancel` — public (no auth); validates token, expiry, booking status
  4. `POST /booking/{token}/reschedule` — public; validates token; proposes new slots
  5. Token expiry: configurable (suggested default: 7 days before appointment start)
- **Pattern:** reuse existing password-reset token pattern (already in codebase)
- **Dependencies:** independent of telephony at schema level; can be built in parallel with T1–T9

### Telephony (`feat/telephony-*`)

- **Planned scope:** T1–T9 as described in §5
- **Status: NOT ON MAIN** — entire block exists in backup snapshot `1ba87f5` commit only
- **Recovery path:**
  - Do NOT merge the snapshot branch
  - Extract T1/T2 to `feat/telephony-t1-t2` (new migration from `demo_user_flag_a1b2c3d4` head)
  - Extract T3, T5, T6, T9 as separate branches in dependency order
  - T7 (DemoSmsProvider) is independent; can be done any time

---

## 11. Risk Register

| # | Risk | Severity | Status |
|---|---|---|---|
| R1 | Production API down (502) | CRITICAL | Active — requires immediate investigation |
| R2 | `staff_invitations` table may exist on production DB but not in `main` codebase | HIGH | UNVERIFIED — requires `alembic current` against production |
| R3 | IVR routes by `business_id` in URL, not phone number | HIGH | Architectural — blocks real telephony pilot |
| R4 | `BusinessMembership.role` not used in auth (SAC-005 incomplete) | HIGH | Architectural — RBAC boundary is weaker than intended |
| R5 | SMS messages are EN-only hardcoded | MEDIUM | Functional — blocks non-English businesses |
| R6 | No public booking management link | MEDIUM | UX — high support burden |
| R7 | Entire telephony block (T1–T9) not on main | HIGH | Feature gap — blocks pilot |
| R8 | No per-business SMS templates | MEDIUM | Feature gap |
| R9 | Landing page does not link to /demo | LOW | Discovery — reduces portfolio value |
| R10 | Node version mismatch (dev Node 26 vs engines `^22.13.0`) | LOW | Build — potential CI/prod discrepancy |
| R11 | No post-deploy production smoke test in CI | MEDIUM | Operational — 502 would not have been caught by CI |

---

## 12. Recommendations

### Immediate (< 1 day)

1. **Investigate and fix production API (502)** — open Railway dashboard, check service logs, identify and resolve the crash/startup failure
2. **Verify production DB schema** — run `alembic current` against Railway Postgres to confirm the migration head matches `demo_user_flag_a1b2c3d4`; if `staff_invitations` or other snapshot tables exist, document and plan remediation

### Short-term (1–3 days)

3. **Add /demo CTA to landing page** — one commit to `frontend/src/app/page.tsx`; < 30 minutes
4. **Add post-deploy smoke test to CI** — add a step after Railway deploy that hits `/health/live` and fails the workflow if it returns non-200

### Next feature work (choose one track)

5. **Track A — Telephony:** Extract T1/T2 (BusinessPhoneNumber model + migration) from snapshot onto a clean branch. This unblocks T3, T5, T6, T9. Build in order: T1/T2 → T3 → T5 → T9 → T6. T7 (DemoSmsProvider) anytime.

6. **Track B — Booking management link:** `feat/public-booking-management-link` — no telephony dependency at schema level. Immediately improves customer UX and reduces support burden.

7. **Track C — SAC-005 RBAC:** Wire `BusinessMembership.role` into authorization context. Closes the RBAC gap without requiring any new models or migrations.

Tracks B and C can be executed in parallel. Track A (telephony) is a prerequisite for real pilot launch with phone calls.

---

## Appendix: Audit File Index

| File | Date | Status |
|---|---|---|
| `docs/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md` | 2026-06-26 | HISTORICAL — preserve; describes recovery from contaminated branch |
| `docs/audits/pre-p3-readiness-audit.md` | 2026-06-19 | HISTORICAL — P2 completion + security/tenancy findings |
| `docs/audits/p3-remaining-backlog-audit.md` | 2026-06-22 | HISTORICAL — P3 backlog reality check; P3 tier now closed (except P3-007 deferred) |
| `docs/audits/staff-access-calendar-current-state.md` | (see file) | HISTORICAL — SAC-00x planning state |
| `docs/audits/AUDIT_CURRENT_REPO_STATE.md` | 2026-06-27 | THIS FILE — current state after recovery + CI/Railway fixes |
