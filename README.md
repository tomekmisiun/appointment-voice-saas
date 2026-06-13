# FastAPI Production Foundation

AI-ready **FastAPI** production foundation for SaaS/API projects with auth,
PostgreSQL, Redis, Docker, CI/CD, observability, and agent workflow rules.
Multi-tenant hooks, background workers, file uploads, and webhooks included.
Use it as a **reusable foundation** — not as a finished SaaS platform or
enterprise-grade product.

**Status (June 2026):** ROADMAP **P0**, **P1**, and **P2** are complete on `main`.
**P3** and open items in `TECH_DEBT.md` are optional future work. See
[`PROJECT_STATUS.md`](PROJECT_STATUS.md) for verified capabilities.

---

## What this is

| | |
|---|---|
| **Is** | A testable API foundation with JWT auth, users, audit logs, Alembic migrations, Redis-backed workers, S3-compatible uploads, webhook idempotency, metrics/logging, deployment scripts, and policy-guarded CI |
| **Is not** | Billing, invites, org membership, managed hosting, or provider-specific production wiring — those belong in your fork |

Clone → configure → extend. Start with [`docs/template-onboarding.md`](docs/template-onboarding.md).

---

## Quick start

**Requirements:** Python 3.13+, [uv](https://docs.astral.sh/uv/), Docker, Docker Compose, Make.

```bash
cp .env.example .env    # set a strong SECRET_KEY
make bootstrap          # compose up, migrate, seed, smoke test
make validate           # ruff + pytest (85% coverage floor)
```

| Resource | URL |
|----------|-----|
| API (local) | http://localhost:8000 |
| OpenAPI / Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health/ready |

Default dev login (after seed): `admin@example.local` / `devpassword123` — change before shared environments. Details: [`app/seed_dev_data.py`](app/seed_dev_data.py).

For day-to-day commands and local modes, see [Local development](#local-development).
Full Makefile reference: [`docs/commands.md`](docs/commands.md).

---

## Feature matrix

| Area | Included in template | Details |
|------|---------------------|---------|
| **Auth & users** | Yes | JWT access/refresh, RBAC, user CRUD, password reset, registration policy, token revocation — [`PROJECT_STATUS.md`](PROJECT_STATUS.md) |
| **PostgreSQL / Alembic** | Yes | SQLAlchemy models, 12 migrations, expand/contract patterns — [`docs/migration-rollback.md`](docs/migration-rollback.md) |
| **Redis** | Yes | Rate limits, caching, job queue, idempotency markers — [`docs/redis-production-contract.md`](docs/redis-production-contract.md) |
| **Background worker** | Yes | Retries, DLQ metadata, maintenance jobs — [`docs/worker-reliability.md`](docs/worker-reliability.md) |
| **File uploads** | Yes | Direct + presigned S3/MinIO, validation hooks — [`docs/file-upload-production.md`](docs/file-upload-production.md) |
| **Webhooks / idempotency** | Yes | HMAC verification, replay window, Redis locks — [`docs/webhook-idempotency.md`](docs/webhook-idempotency.md) |
| **Observability** | Partial | Request IDs, structured logs, Prometheus metrics, optional Sentry; local Grafana/Loki/Prometheus configs — [`docs/observability-production.md`](docs/observability-production.md) |
| **Docker** | Yes | Dev Compose stack (API, worker, Postgres, Redis, MinIO) — [`Dockerfile`](Dockerfile), [`docker-compose.yml`](docker-compose.yml) |
| **CI/CD** | Yes | Pre-commit, pytest + coverage, policy guards, Trivy, dependency review, deploy/release workflows — [`.github/workflows/`](.github/workflows/), [`docs/ci-policy-guards.md`](docs/ci-policy-guards.md) |
| **AI workflow** | Yes | Binding rules in [`.ai-rules/`](.ai-rules/), optional [`agents/`](agents/) & [`.commands/`](.commands/) — [`docs/ai-workflows.md`](docs/ai-workflows.md), [`AGENTS.md`](AGENTS.md) |

Multi-tenant isolation, platform admin boundaries, and legacy route policy: [`docs/tenant-isolation.md`](docs/tenant-isolation.md), [`docs/platform-admin-model.md`](docs/platform-admin-model.md), [`docs/legacy-route-deprecation.md`](docs/legacy-route-deprecation.md).

---

## Local development

The default path is **Docker Compose-first**: API, worker, Postgres, Redis, and
MinIO run in containers. Most `make` targets exec into the `api` service.

**First setup** (once after `cp .env.example .env`):

```bash
make bootstrap    # compose up, migrate, seed, smoke
```

**Daily commands**:

| Command | Purpose |
|---------|---------|
| `make docker-up` / `make docker-down` | Start / stop the Compose stack |
| `make test` / `make test-coverage` | Pytest in the API container |
| `make lint` / `make lint-fix` | Ruff check (with optional auto-fix) |
| `make validate` | Ruff + pytest with 85% coverage floor (CI-equivalent gate) |
| `make migration-upgrade` | Apply Alembic migrations (`upgrade head`) |

**Local modes**

| Mode | When to use | Typical flow |
|------|-------------|--------------|
| **Compose-first** (default) | Normal development and parity with CI | `make docker-up` → edit code → `make test` / `make lint` / `make validate` |
| **Host API** | Faster uvicorn reload on the host without the Compose `api` container | `make install` → `make run` — Postgres, Redis, and MinIO must still be reachable (usually `make docker-up` without relying on the `api` service, or external URLs in `.env`) |

Seeding, smoke checks, policy guards, backups, deploy dry-runs, and load tests
are documented in [`docs/commands.md`](docs/commands.md). Troubleshooting:
[`docs/troubleshooting.md`](docs/troubleshooting.md).

---

## Project structure

| Path | Purpose |
|------|---------|
| [`app/api/`](app/api/) | Routes, dependencies, OpenAPI helpers |
| [`app/services/`](app/services/) | Business logic (domain errors, no HTTP in services) |
| [`app/models/`](app/models/) | SQLAlchemy models |
| [`app/schemas/`](app/schemas/) | Pydantic request/response models |
| [`app/core/`](app/core/) | Config, security, middleware, metrics |
| [`app/worker.py`](app/worker.py) | Background job consumer |
| [`alembic/`](alembic/) | Migrations |
| [`tests/`](tests/) | Pytest suite (~374 tests, ~88% coverage) |
| [`scripts/`](scripts/) | Deploy, backup, smoke, CI guards |
| [`.github/workflows/`](.github/workflows/) | CI, release, deploy, backup workflows |
| [`docs/`](docs/) | Runbooks and onboarding |
| [`.ai-rules/`](.ai-rules/) | Binding AI/project rules |
| [`observability/`](observability/) | Example Prometheus / Grafana / Loki configs |

Architecture decision: sync-first API — [`docs/adr/0001-sync-vs-async-architecture.md`](docs/adr/0001-sync-vs-async-architecture.md).

---

## Documentation map

### New project onboarding

| Document | Purpose |
|----------|---------|
| [`docs/template-onboarding.md`](docs/template-onboarding.md) | Clone → rename → configure → first deploy path |
| [`docs/template-usage.md`](docs/template-usage.md) | Quick reuse reference |
| [`TEMPLATE_FREEZE_CHECKLIST.md`](TEMPLATE_FREEZE_CHECKLIST.md) | Template freeze / validation checklist |

### Local development

| Document | Purpose |
|----------|---------|
| [`docs/commands.md`](docs/commands.md) | Full Makefile target reference by category |
| [`.env.example`](.env.example) | Environment variable reference (full list) |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common local and CI failures |
| [`docs/ci-policy-guards.md`](docs/ci-policy-guards.md) | Pre-commit and CI guard rules |
| [`docs/load-concurrency-testing.md`](docs/load-concurrency-testing.md) | Load and concurrency testing |
| [`perf/README.md`](perf/README.md) | Load baseline profiles |

### Production deployment

| Document | Purpose |
|----------|---------|
| [`docs/production-deployment.md`](docs/production-deployment.md) | Staging/production operating model |
| [`docs/production-runtime-examples.md`](docs/production-runtime-examples.md) | Reverse proxy and runtime examples |
| [`docs/migration-rollback.md`](docs/migration-rollback.md) | Migration rollout and rollback |
| [`docs/database-backup-restore.md`](docs/database-backup-restore.md) | Logical backup and restore |
| [`docs/backup-restore-automation.md`](docs/backup-restore-automation.md) | Scripted backup workflows |
| [`docs/pitr-and-scheduled-backups.md`](docs/pitr-and-scheduled-backups.md) | PITR checklist and scheduled backups |

### Security & operations

| Document | Purpose |
|----------|---------|
| [`docs/secret-management.md`](docs/secret-management.md) | Secrets and rotation expectations |
| [`docs/tenant-isolation.md`](docs/tenant-isolation.md) | Tenant scoping and cross-tenant tests |
| [`docs/malware-scanning.md`](docs/malware-scanning.md) | Upload malware scanner integration |
| [`docs/redis-production-contract.md`](docs/redis-production-contract.md) | Production Redis expectations |
| [`docs/webhook-idempotency.md`](docs/webhook-idempotency.md) | Webhook verification patterns |

### AI agent workflow

| Document | Purpose |
|----------|---------|
| [`docs/ai-workflows.md`](docs/ai-workflows.md) | How rules, personas, and commands fit together |
| [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md) | Tool entry indexes → `.ai-rules/` |
| [`.ai-rules/`](.ai-rules/) | Binding architecture, security, git, testing rules |
| [`agents/`](agents/) | Optional review personas |
| [`.commands/`](.commands/) | Optional copy-paste agent prompts |

---

## Production readiness

| Milestone | Status |
|-----------|--------|
| **P0** — production blockers (June 2026 audit) | **Complete** — merged PRs #45–#54 |
| **P1** — adoption hardening | **Complete** — merged PRs #56–#67 |
| **P2** — scale & maintainability | **Complete** — merged PRs #69–#82 |
| **P3** — enterprise-scale optional | **Not started** — see [`ROADMAP.md`](ROADMAP.md) |
| **Open tech debt** | **9 items** — see [`TECH_DEBT.md`](TECH_DEBT.md) |
| **Template freeze** | **Ready** — tag [`v1.0.0`](https://github.com/tomekmisiun/fastapi-production-foundation/releases/tag/v1.0.0) on freeze commit |

Verified test baseline: **374** pytest tests, **~88%** line coverage, **85%** floor in CI and `make validate`. Authoritative feature list: [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

---

## What your fork must still configure

The template ships patterns and runbooks, not a live production environment. Each downstream project still chooses and wires:

| Area | You provide |
|------|-------------|
| **Hosting** | Kubernetes, PaaS, VM, or other runtime target |
| **Secrets** | Secret manager, rotation, and GitHub Environment secrets |
| **Data stores** | Managed PostgreSQL, HA Redis, and object storage |
| **Backups** | Provider, RPO/RTO, and PITR policy (scripts exist; PITR is provider-specific) |
| **Malware scanning** | Concrete scanner URL (production validator requires one) |
| **Alerting** | PagerDuty, Slack, or other on-call routing (local Alertmanager is an example) |
| **Tracing** | Sentry, OpenTelemetry, or both beyond the optional Sentry hook |
| **API clients** | Migration from deprecated unversioned routes to `/api/v1` |
| **Product policy** | Registration, roles, billing, and tenant lifecycle for your domain |

---

## Tracking & roadmap

| File | Purpose |
|------|---------|
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | **Verified** implemented capabilities only |
| [`ROADMAP.md`](ROADMAP.md) | Prioritized planned work (P3 next) |
| [`TECH_DEBT.md`](TECH_DEBT.md) | Known debt register |

**License:** see repository license file. **Contributing:** feature branches + PR; run `make validate` before merge.
