# Inherited Foundation Project Status

This is historical FastAPI Production Foundation status preserved from before
this repository became Appointment Voice SaaS. It is not the active product
status. Active product status lives in `../../PROJECT_STATUS.md`.
Links in the preserved body below refer to the original foundation-era root
filenames; use this `docs/foundation/` directory for the archived foundation
versions.

---

# Project Status

Verified implementation state of **FastAPI Production Foundation** — an
AI-ready, production-oriented FastAPI foundation for SaaS/API projects.
Planned work: `ROADMAP.md`. Known issues: `TECH_DEBT.md`.

Do not treat this file as a roadmap or debt register.

## Overview

Reusable, **AI-ready** FastAPI production foundation for SaaS/API projects — a
testable foundation, not a finished multi-tenant SaaS platform or
enterprise-grade product.

**Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, S3-compatible
storage, Docker Compose, pytest, Ruff, uv, GitHub Actions.

**Test baseline (verified):** 374 pytest tests, ~88% line coverage, 85%
coverage floor enforced in CI and `make validate`.

**Production readiness (June 2026):**

- **P0 blockers closed** — all ten ROADMAP P0 tasks (#1–#10) are implemented,
  tested, and merged to `main` (PRs #45–#54).
- **P1 adoption hardening closed** — all twelve ROADMAP P1 tasks (#11–#22) are
  implemented, tested, and merged to `main` (PRs #56–#67).
- **P2 scale and maintainability closed** — all fourteen ROADMAP P2 tasks
  (#23–#36) are implemented, tested, and merged to `main` (PRs #69–#82).
- **Template scope unchanged** — not a fully configured production environment;
  forks still choose hosting, secrets, backups, scanners, and product policies.
- **Next engineering priority** — ROADMAP **P3** (enterprise-scale optional
  improvements). See `ROADMAP.md`.
- **Template freeze (June 2026)** — suitable as a cloneable, AI-ready foundation;
  see `TEMPLATE_FREEZE_CHECKLIST.md` and `docs/ai-workflows.md`.

**Architecture:**

- API routes: `app/api/routes`
- API dependencies: `app/api/dependencies`
- Business logic: `app/services`
- Models: `app/models`
- Schemas: `app/schemas`
- Database session: `app/db/session.py`
- Core config/security/infra: `app/core`
- Migrations: `alembic/versions` (12 revisions)
- Tests: `tests/` (54 modules)

**Documentation and rules:**

- `README.md` — landing page, quick start, doc navigation
- `docs/` — deployment, security, workers, tenancy, backups, load testing
- `.ai-rules/` — binding AI/project rules (source of truth for agent behavior)
- `docs/ai-workflows.md` — how `.ai-rules/`, `agents/`, and `.commands/` fit together
- `agents/`, `.commands/` — optional review personas and copy-paste prompts
- `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/*.mdc` — thin wrappers pointing to `.ai-rules`
- `TEMPLATE_FREEZE_CHECKLIST.md` — template reuse and validation checklist

---

## Verified Capabilities

### Application core

- FastAPI bootstrap with versioned API (`/api/v1`) and deprecated legacy
  unversioned routes gated by `LEGACY_ROUTES_ENABLED` (default off in
  production; policy in `docs/legacy-route-deprecation.md`)
- Centralized error envelope for HTTP, validation, auth, not-found, rate-limit,
  and domain errors raised from services
- Request ID middleware (`X-Request-ID`, `X-Process-Time`) with structured
  logging (`text`/`json`), sensitive-field redaction, and worker job
  `request_id` correlation
- Production/staging config validation rejecting weak secrets, local/default
  remote service placeholders, unsafe upload/metrics defaults, and missing
  proxy/rate-limit settings in production (`app/core/config.py`)
- Effective DB pool settings logged at API startup (`app/db/pool_config.py`;
  sizing guidance in `docs/production-deployment.md`)
- CORS, trusted hosts, and security headers middleware (env-driven)
- Optional Sentry error tracking (disabled without `SENTRY_DSN`)

### Authentication and sessions

- Registration with `REGISTRATION_POLICY` (`public` | `disabled`)
- Login with bcrypt-hashed passwords and JWT access + refresh tokens (signing
  algorithm from `settings.algorithm`)
- `/auth/me`, `/auth/refresh`, `/auth/logout`
- Refresh token rotation with Redis-backed `jti` revocation
- Access token invalidation via per-user `token_version` (password reset,
  deactivation, role change)
- Inactive users blocked on login, access, and refresh
- Redis rate limits on `/auth/login`, `/auth/register`, and password-reset
  request (per-IP with optional trusted forwarded headers; reset also keyed by
  email hash)
- Password reset request/confirm with hashed single-use tokens, SMTP email
  abstraction, worker job delivery, audit log entries, and expired-token
  cleanup maintenance

### Authorization and users

- RBAC roles: `user`, tenant `admin`, `platform_admin` with static permission
  map (`app/core/permissions.py`)
- Tenant `admin` excludes `tenants.*`; `platform_admin` includes tenant
  lifecycle permissions
- Admin `/admin` endpoint; user CRUD, activate/deactivate, self-read/update
- Admin role updates validated against `UserRole` enum (`user`, `admin`,
  `platform_admin`); invalid values return 422
- User listing with keyset cursor pagination (legacy offset fallback), sorting,
  filters, and email search (`search_mode`: prefix default, optional contains
  with pg_trgm)
- Redis-backed user-list cache with tenant-scoped keys and invalidation on writes
- Audit log model, indexes, admin listing, and writes for admin user actions

### Multi-tenancy

- Tenant model with default tenant via `ensure_default_tenant()` / `make seed-tenant`;
  migration `a1b2c3d4e5f6` also idempotently backfills `default` on upgrade (no
  fixed `id=1`)
- `X-Tenant-Slug` resolution for unauthenticated flows; JWT `tenant_id` on
  authenticated requests with optional header cross-check
- Tenant-scoped users (unique `(tenant_id, email)`), audit logs, uploads, cache
  keys, and object key prefixes
- Tenant lifecycle API for `platform_admin`; cross-tenant denial tests

### Files and storage

- Multipart upload and presigned upload/complete/download/delete flows
- Presigned complete returns `verification_status` (`pending` → worker verify);
  download blocked with 409 until verified
- S3-compatible storage abstraction with module-level cached boto3 client (MinIO in
  local Compose)
- Streaming multipart upload for direct uploads (no full in-memory buffer)
- Size limits, content-type allowlist, magic-byte sniffing (PNG/JPEG/PDF)
- Malware scanner integration point (disabled by default in dev; production
  requires enabled scan + HTTP scanner URL; documented in
  `docs/malware-scanning.md`)
- Private object keys under `tenants/{tenant_id}/uploads/{owner_id}/...`

### Webhooks and idempotency

- `POST /api/v1/webhooks/inbound` with timestamped HMAC verification and replay
  window
- Event deduplication on `(provider, event_id)`; payload stored as hash only
- Redis in-flight lock and persisted idempotency response cache

### Background worker

- Redis job queue with main, processing, delayed, and failed queues
- Stale processing-queue reaper before dequeue (visibility timeout configurable)
- Unknown job types routed to failed queue (no silent acknowledge)
- Exponential backoff retries, DLQ metadata, maintenance lock, and tunable
  maintenance/promote loop
- Password-reset email job with Redis completion marker keyed by `job.id`
- Failed-job inspection/requeue CLI (`app/worker_failed_jobs.py`)
- Docker Compose worker service

### Health and metrics

- `/health`, `/health/live`, `/health/ready` (DB + Redis), `/health/db`,
  `/health/redis`
- Prometheus `/metrics` with optional bearer auth (`METRICS_REQUIRE_AUTH`,
  default on in production) and HTTP, dependency, and worker counter
  instrumentation in-process
- Optional Prometheus multiprocess aggregation via `PROMETHEUS_MULTIPROC_DIR`

### Local observability stack

Verified in repo:

- `docker-compose.observability.yml`
- `.env.observability.example` (copy to `.env.observability` for local Grafana auth)
- Prometheus (`observability/prometheus/`) with scrape config and alert rules
- Loki, Promtail (compose service discovery for the `api` container), Alertmanager
- Grafana with Loki and Prometheus datasource provisioning
- Provisioned `FastAPI Overview` dashboard under `observability/grafana/dashboards`

Local Alertmanager uses a no-op receiver stub; see `observability/alertmanager/README.md`.

### Docker and CI/CD

- Multi-stage `Dockerfile` (development/production targets, non-root user)
- Local Compose: api, worker, db, test_db, redis, minio
- Minimal `docker-compose.prod.yml` (api + worker image only)
- CI: pre-commit, pytest with 85% coverage, backup/restore rehearsal,
  load-smoke, Trivy CRITICAL/HIGH gate, dependency review on PRs
- Release workflow (GHCR image on tag), manual deploy workflow with dry-run
  default, promotion scripts, optional migrations and smoke checks
- Dependabot for uv, GitHub Actions, and Docker base image
- Scheduled backup workflow example (requires operator secrets/hooks)

### Operations tooling

- Alembic migrations with Makefile helpers; migration downgrade rehearsal tests
- `scripts/db_backup.sh`, `db_restore_rehearsal.sh` with CI rehearsal
- `perf/load_baseline.py`, load threshold profiles, CI load-smoke job
- `make bootstrap`, `make smoke`, `make validate`, development seed data, and
  `make seed-tenant` for default tenant provisioning
- Runbooks in `docs/` for deployment, secrets, migrations, backups, workers,
  tenant isolation, observability, Redis production contract, and template
  onboarding

---

## What this template does not include

See `ROADMAP.md` (P1–P3) and `TECH_DEBT.md` for tracked gaps. Examples:

- Real malware scanner service (integration boundary only; operator must wire URL)
- Webhook processing pipeline, OAuth/MFA, PostgreSQL RLS

---

## Updating this file

Update after merged work that changes behavior, architecture, setup, tests,
migrations, or CI.

- Add only **verified** capabilities (code + tests exist).
- Do not list planned work here — use `ROADMAP.md`.
- Do not list open defects here — use `TECH_DEBT.md`.
- Keep `.ai-rules` as the source of truth for AI behavior rules.
