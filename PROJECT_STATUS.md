# Project Status — VoxSlot

This file summarizes verified capabilities only. The fuller implementation
snapshot is [`docs/project/current-state.md`](docs/project/current-state.md).

Last documentation audit: 2026-06-28.

## Current Summary

| Area | Status | Evidence |
|---|---|---|
| Local development | Ready | `docker-compose.yml`, `Makefile`, seed scripts, backend/frontend tests. |
| Core booking backend | Implemented | Models, migrations, routes, services, and tests under `app/`, `alembic/`, `tests/`. |
| IVR and Twilio voice | Implemented | `app/api/routes/twilio_voice.py`, `app/services/ivr_service.py`, Twilio security tests. |
| SMS notifications | Implemented | `NotificationOutbox`, SMS providers, worker tests, Twilio SMS routes. |
| Calendar boundary | Partial | Calendar models/fake provider/worker sync exist; real OAuth/setup UI does not. |
| Owner dashboard | Partial | Auth, dashboard, bookings, staff, demo routes exist; many configuration screens remain. |
| Public read-only demo | Implemented but environment-dependent | Demo endpoint, middleware, seed data, frontend `/demo`, contract tests. |
| Railway deployment | Configured | `railway.api.toml`, `railway.worker.toml`, `frontend/railway.toml`, CI deploy job. |
| Production SaaS readiness | Not ready | Active gaps in `TECH_DEBT.md`; production status requires live verification. |

## Verified Implemented Capabilities

- Multi-tenant FastAPI backend with `/api/v1` product routes.
- JWT auth, refresh tokens, token invalidation, role hierarchy based on
  `User.role`.
- Tenant/business domain: businesses, staff, services, working hours,
  availability exceptions, recurring staff blocks, bookings, clients,
  customers, waitlist entries, audit logs, uploaded files, calendar state,
  notification outbox, owner leads.
- Availability generation from schedules, exceptions, recurring blocks,
  existing bookings, business timezone, and staff/business intersections.
- Booking create/list/read/cancel/reschedule/admin override and pending-payment
  hold state.
- Database-level appointment overlap protection.
- IVR simulator and Twilio voice webhooks with signature validation.
- SMS confirmation/cancellation/reminder/waitlist flows through queued outbox
  work.
- Redis-backed queues, retry/backoff, failed-job tracking, delayed work, rate
  limiting, cache, and idempotency.
- S3-compatible presigned upload/download flow with local MinIO.
- Prometheus metrics, health/readiness endpoints, optional Sentry integration,
  and local observability configuration.
- Next.js frontend with landing/register/login/demo/dashboard/bookings/staff
  surfaces and generated OpenAPI TypeScript types.
- CI jobs for pre-commit, policy guards, secret scanning, backend tests with
  coverage, load smoke, Docker build/Trivy, frontend validation, public demo
  contract, and Railway deploy on `main`.

## Partial Or Not Implemented

| Area | Current state |
|---|---|
| Per-business RBAC | `BusinessMembership` exists; runtime authorization still uses `User.role`. |
| Calendar production setup | Calendar models and fake provider exist; no real OAuth flow or frontend setup screen. |
| Multi-service workflow | Data model and availability support exist; IVR and primary booking create flow are not fully multi-service. |
| Owner dashboard | Booking and staff views exist; service, hours, exception, recurring block, client, metrics, calendar, and telephony screens remain. |
| Telephony inventory | `BusinessPhoneNumber` and `telephony_status` are not on `main`; Twilio voice routing uses `Business.phone`. |
| Customer self-service | No public HMAC booking management link. |
| Billing | Stripe links, subscriptions, and plan enforcement are not implemented. |
| Browser E2E | No Playwright/Cypress suite. |

## Readiness

| Target | Status | Notes |
|---|---|---|
| Local development | Ready | Run `make bootstrap`, seed demo data, and start frontend. |
| Local portfolio demo | Ready | Uses fake/local providers and deterministic demo seed. |
| Controlled pilot | Not ready without owner approval | Real provider configuration and open gaps must be reviewed first. |
| Public production demo | Not guaranteed | Must verify current Railway API/frontend health before use. |
| General production SaaS | Not ready | Billing, provisioning, RBAC cutover, owner UX, production smoke, and other gaps remain. |

## Update Rules

- Add only capabilities verified from code, migrations, tests, CI, or deployment
  configuration.
- Keep detailed future work in [`ROADMAP.md`](ROADMAP.md).
- Keep active gaps in [`TECH_DEBT.md`](TECH_DEBT.md).
- Refresh [`docs/project/current-state.md`](docs/project/current-state.md) when implementation
  status changes materially.
