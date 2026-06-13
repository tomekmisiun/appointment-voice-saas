# Template Freeze Checklist

Use this document to decide whether a clone of this repository is a practical
backend foundation, and what to do immediately after cloning.

**Freeze status (June 2026):** This repository is **ready to freeze** as a
reusable template. Optional improvements remain in `ROADMAP.md` P3 and
`TECH_DEBT.md`; they do not block cloning, local development, validation, or
documented production deployment patterns.

For step-by-step onboarding, see `docs/template-onboarding.md` and
`docs/template-usage.md`.

---

## What Is Included

- **API core:** FastAPI app, versioned routes (`/api/v1`), legacy route gate,
  standard error envelope, request ID logging, security headers, CORS, trusted
  hosts.
- **Auth & users:** Register/login, JWT access + refresh with rotation,
  password reset, RBAC (`user`, `admin`, `platform_admin`), user CRUD, session
  revocation via `token_version`.
- **Multi-tenancy:** Tenant model, default tenant seed, tenant-scoped data paths,
  platform admin tenant lifecycle API.
- **Data layer:** SQLAlchemy models, Alembic migrations (12 revisions), Postgres
  in Compose, pool config logging.
- **Redis:** Rate limits, refresh revocation, cache, idempotency locks, job
  queue; production contract documented.
- **Worker:** Redis queue, retries, DLQ, maintenance jobs (retention, password
  reset email), graceful shutdown, Prometheus metrics on `:9100`.
- **Files:** S3-compatible storage (MinIO locally), multipart + presigned flows,
  upload validation, malware scanner integration boundary.
- **Webhooks & idempotency:** Inbound webhook verification, deduplication,
  idempotency records.
- **Observability:** Health/readiness, Prometheus `/metrics`, optional Sentry,
  local observability Compose stack (Prometheus, Loki, Grafana).
- **Ops & CI:** `make validate`, backup/restore scripts, deploy/release
  workflows, load-smoke CI, Trivy gate, policy guards, 374 tests / 85% coverage
  floor.
- **AI agent workflow:** `.ai-rules/` binding rules, optional `agents/` personas,
  `.commands/` prompts, `docs/ai-workflows.md` (see `AGENTS.md`).

---

## What Is Intentionally Not Included

Do **not** expect these in the template (add them in your product repo):

- Billing, subscriptions, invoices, or payment providers
- Invite-only registration flows, OAuth/SAML/MFA
- Product-specific domain modules (bookings, catalog, orders, etc.)
- Managed hosting, secrets store, or backup provider wiring
- A running malware scanner service (integration URL only)
- PostgreSQL RLS (optional P3 example)
- Full E2E worker email integration test in CI (P3)
- One-click production deploy without operator configuration

See `ROADMAP.md` P3 and `TECH_DEBT.md` for tracked optional work.

---

## First Steps After Cloning

1. **Rename metadata** — README title, dev seed emails (`app/seed_dev_data.py`),
   optional `APP_NAME`, and example image paths in docs/Makefile dry-run if you
   use them.
2. **Configure env** — `cp .env.example .env`; set a strong `SECRET_KEY`.
3. **Bootstrap locally** — `make bootstrap` (Compose, migrations, seed-tenant,
   dev seed, smoke).
4. **Validate** — `make validate` (Ruff + pytest with 85% coverage floor).
5. **Read production docs** before staging/production:
   `docs/production-deployment.md`, `docs/production-runtime-examples.md`,
   `docs/secret-management.md`, `docs/redis-production-contract.md`.
6. **Configure GitHub** — Environments `staging` / `production`; see GitHub
   checklist in `docs/production-runtime-examples.md`.
7. **Add your domain** — new models, services, routes under `app/`; register
   router in `app/api/v1.py`; create Alembic migration.

---

## Local Startup Checklist

| Step | Command | Notes |
|------|---------|-------|
| Install deps (host) | `make install` or `uv sync` | Optional if using Docker only |
| Env file | `cp .env.example .env` | Never commit `.env` |
| Full stack | `make bootstrap` | Recommended first run |
| Or manual | `make docker-up && make migration-upgrade && make seed-tenant && make seed && make smoke` | Dev seed is not for production |
| Tests | `make validate` | Same floor as CI |
| Policy guards | `make policy-guards` | Migration/model/CI policy scripts |
| API only (host) | `make run` | Requires local Postgres/Redis or adjusted env |
| Observability (optional) | `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d` | Copy `.env.observability.example` |

Default URLs: API `http://localhost:8000`, docs `/docs`, health `/health/ready`.

---

## Required Environment Variables

### Always (all environments)

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT signing; min 32 chars; no known placeholders |
| `ENVIRONMENT` | `development` \| `test` \| `staging` \| `production` |
| `DATABASE_URL` | PostgreSQL connection string |
| `TEST_DATABASE_URL` | Test database (pytest) |

### Local Docker defaults (change for shared staging/production)

| Variable | Local default | Production expectation |
|----------|---------------|------------------------|
| `REDIS_HOST` | `redis` | Managed Redis hostname |
| `REDIS_PASSWORD` | empty | Required for remote Redis |
| `S3_*` | MinIO defaults | Real object storage credentials |
| `SMTP_*` / `EMAIL_FROM` | empty / example | Real mail provider |
| `PASSWORD_RESET_URL` | localhost | Public HTTPS URL |

### Production-enforced (startup validation)

When `ENVIRONMENT=production`, the app **fails startup** unless configured safely:

- Strong `SECRET_KEY` (no placeholders)
- Non-local `DATABASE_URL`, Redis host, S3 endpoint/credentials/bucket
- `TRUSTED_HOSTS_ENABLED=true` with real hostnames
- `RATE_LIMIT_TRUST_FORWARDED_HEADERS=true` (reverse proxy deployments)
- No wildcard CORS with credentials
- `METRICS_REQUIRE_AUTH=true` and non-empty `METRICS_BEARER_TOKEN` (default)
- If file uploads are used: `UPLOAD_MALWARE_SCAN_ENABLED=true` and
  `UPLOAD_MALWARE_SCANNER_URL` set
- Non-localhost `PASSWORD_RESET_URL`, non-example `EMAIL_FROM`
- `LEGACY_ROUTES_ENABLED` defaults to **off** in production

Full inventory: `.env.example`, `docs/secret-management.md`,
`docs/production-deployment.md`.

---

## Production Deployment Checklist

1. Choose hosting (K8s, PaaS, VM + Compose) and runtime shape (replicas vs
   in-process workers — see `docs/production-runtime-examples.md`).
2. Provision managed PostgreSQL, Redis (HA per `docs/redis-production-contract.md`),
   and S3-compatible storage.
3. Set production `.env` on the host or secret manager; run config validation
   (`ENVIRONMENT=production`).
4. Run migrations (`make migration-upgrade` or deploy workflow migration step).
5. Deploy `api` + `worker` from promoted image (`docker-compose.prod.yml` or
   your orchestrator).
6. Terminate TLS at reverse proxy; configure forwarded headers and trusted hosts.
7. Restrict `/metrics` to internal network or bearer auth.
8. Wire malware scanner URL if uploads are enabled.
9. Configure GitHub Environments, release tags, and deploy workflow smoke checks.
10. Set up backups (`docs/backup-restore-automation.md`) and observability
    scraping (API + worker `:9100`).

---

## Unsafe Defaults to Override

| Default | Risk | Action |
|---------|------|--------|
| Docker Compose DB/Redis/MinIO credentials | Public if ports exposed | Use only locally; replace in staging/prod |
| `SECRET_KEY` placeholder in `.env.example` | Token forgery | Generate before any shared deploy |
| Single-process Uvicorn in production image | CPU saturation on one core | Override CMD or scale replicas (documented) |
| `UPLOAD_MALWARE_SCAN_ENABLED=false` in dev | Unsafe if copied to prod | Production validator blocks this |
| `REGISTRATION_POLICY=public` | Open signup | Set `disabled` or add product-level invite flow |
| Example GHCR paths in Makefile dry-run | Confusion only | Replace with your registry path |

Production startup validators in `app/core/config.py` block many unsafe
combinations when `ENVIRONMENT=production`.

---

## Adding a Business Domain Module

Follow existing layers (see `.ai-rules/architecture.md`):

1. `app/models/<domain>.py` — SQLAlchemy model(s)
2. `alembic/versions/` — migration
3. `app/schemas/<domain>.py` — Pydantic schemas
4. `app/services/<domain>_service.py` — business logic; raise `DomainError`, not
   `HTTPException`
5. `app/api/routes/<domain>.py` — HTTP wiring, permissions
6. Register router in `app/api/v1.py`
7. `tests/test_<domain>.py` — behavior tests

Keep tenant scoping, permissions, and audit patterns consistent with existing
modules.

---

## Known Non-Blocking Limitations

- Open `TECH_DEBT.md` items (9): RLS example, OTel, adversarial tests, E2E worker
  test, script tests, observability CI lint, extended migration tests, adapter
  coverage gaps, CSP header.
- `email_service.py` and `tenant_seed_service.py` have lower unit-test coverage;
  paths are exercised indirectly.
- Gunicorn is documented but not installed in the base image.
- Default tenant migration backfill remains for upgrade safety; canonical seed is
  `make seed-tenant` (see `docs/tenant-isolation.md`).
- Template does not enforce `DEBUG=false`; rely on `ENVIRONMENT=production` and
  deployment docs.

---

## Validation Commands (Verified June 2026)

```bash
make validate              # ruff + pytest --cov-fail-under=85
make policy-guards         # CI policy scripts + AI workflow presence
make validate-ai-workflows # AI rules / agents / commands only
make bootstrap             # local full stack + smoke (optional but recommended once)
```

Expected: **374 tests passed**, coverage ≥ 85%.
