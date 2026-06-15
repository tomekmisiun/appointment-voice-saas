# Makefile command reference

All targets are defined in [`Makefile`](../Makefile). This document groups them
by purpose. For day-to-day local work, start with the
[Local development](../README.md#local-development) section in `README.md`.

## First setup

| Target | Purpose |
|--------|---------|
| `make install` | Install Python dependencies on the host with `uv sync`. Used for host API mode; Compose builds dependencies inside the API image. |
| `make bootstrap` | One-shot first run: `docker-up` → `migration-upgrade` → `seed-tenant` → `seed` → `smoke`. Use after copying `.env.example` to `.env`. |

## Daily development

| Target | Purpose |
|--------|---------|
| `make docker-up` | Build and start the Compose stack in the background (`docker compose up --build -d`). |
| `make docker-down` | Stop and remove Compose containers (`docker compose down`). |
| `make run` | Run the API on the host with `uvicorn --reload` (without the Compose `api` service). Supporting services (Postgres, Redis, MinIO) must still be reachable via `.env`. |
| `make test` | Run pytest inside the running `api` container (`docker compose exec api pytest -v`). |
| `make test-parallel` | Run pytest across `PYTEST_WORKERS` (default 2) isolated pytest-xdist workers, each with its own test database and Redis DB (see `tests/xdist_isolation.py`). |
| `make test-coverage` | Pytest with coverage report and an **85%** floor (`--cov-fail-under=85`). |
| `make lint` | Ruff check inside the `api` container. |
| `make lint-fix` | Ruff check with `--fix` inside the `api` container. |
| `make validate` | Full local gate: Ruff + pytest with coverage floor (same intent as CI). Override floor with `COVERAGE_FAIL_UNDER=85`. |

## Testing and validation

| Target | Purpose |
|--------|---------|
| `make smoke` | HTTP smoke script against a running API. Variables: `API_BASE_URL` (default `http://localhost:8000`), `DEV_ADMIN_EMAIL`, `DEV_PASSWORD`. |
| `make validate` | See [Daily development](#daily-development). |

## Database and migrations

| Target | Purpose |
|--------|---------|
| `make migration-current` | Show the current Alembic revision. |
| `make migration-heads` | Show Alembic head revisions. |
| `make migration-upgrade` | Apply migrations (`alembic upgrade head`). |

See also [`docs/migration-rollback.md`](migration-rollback.md).

## Seeding

Development-only data loaders. Re-run when resetting local state; not part of the
daily edit/test loop.

| Target | Purpose |
|--------|---------|
| `make seed-tenant` | Create the default tenant (`python -m app.seed_default_tenant`). |
| `make seed` | Load dev users and sample data (`python -m app.seed_dev_data`). |

`make bootstrap` runs both seed targets automatically.

## CI and policy guards

Maintainer and CI checks. See [`docs/ci-policy-guards.md`](ci-policy-guards.md).

| Target | Purpose |
|--------|---------|
| `make policy-guards` | Run repository policy scripts (`scripts/ci/run_policy_guards.sh`). |
| `make validate-ai-workflows` | Verify required AI workflow files (`scripts/validate-ai-workflows.sh`). Included in `make policy-guards`. |

## Backup and restore

Ops and reliability scripts. See [`docs/database-backup-restore.md`](database-backup-restore.md)
and [`docs/backup-restore-automation.md`](backup-restore-automation.md).

| Target | Purpose |
|--------|---------|
| `make db-backup` | Logical PostgreSQL backup via `scripts/db_backup.sh`. Variables: `BACKUP_DIR`, `BACKUP_FILE`, `DB_NAME`, `DB_SERVICE`, `DB_USER`. |
| `make db-restore-check` | Restore rehearsal into a separate database via `scripts/db_restore_rehearsal.sh`. Variable: `RESTORE_CHECK_DB`. |
| `make db-backup-dry-run` | Print backup command without executing (`DRY_RUN=true`). |
| `make db-restore-check-dry-run` | Print restore-check command without executing (`DRY_RUN=true`). |

## Deploy and release

| Target | Purpose |
|--------|---------|
| `make deploy-dry-run` | Simulate promotion/deploy without applying changes. Variables: `ENVIRONMENT` (default `staging`), `IMAGE_TAG` (default `latest`). Sets `DRY_RUN=true` and `RUN_MIGRATIONS=true`. |

Release images are built by the GitHub **Release** workflow on `v*` tags, not by
Makefile targets. See [`docs/production-deployment.md`](production-deployment.md).

## Load and performance

Lightweight latency and throughput checks. See
[`docs/load-concurrency-testing.md`](load-concurrency-testing.md) and
[`perf/README.md`](../perf/README.md).

Shared variables (defaults shown in `Makefile`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOAD_REQUESTS` | `50` | Total requests per run |
| `LOAD_CONCURRENCY` | `5` | Concurrent workers |
| `LOAD_API_BASE_URL` | `http://api:8000` | Base URL from inside Compose |
| `LOAD_MAX_P95_MS` | (unset) | Optional p95 ceiling when using `--check-thresholds` |
| `LOAD_MAX_P99_MS` | (unset) | Optional p99 ceiling |
| `LOAD_MIN_THROUGHPUT_RPS` | (unset) | Optional minimum throughput |

| Target | Purpose |
|--------|---------|
| `make load-smoke` | Baseline load against default health path. |
| `make load-smoke-ready` | Load against `/health/ready`. |
| `make load-smoke-thresholds` | Health profile with threshold enforcement. |
| `make load-smoke-ready-thresholds` | Readiness profile with threshold enforcement. |
| `make load-validate` | Run `load-smoke-thresholds` then `load-smoke-ready-thresholds`. |
| `make load-smoke-auth-login` | Auth login profile (no threshold check). |
| `make load-smoke-auth-login-thresholds` | Auth login profile with fixed small request counts and threshold check. |
| `make load-smoke-ci` | Lighter threshold check used in CI (see `.github/workflows/ci.yml`). |

## Composite targets

| Target | Runs |
|--------|------|
| `make bootstrap` | `docker-up` → `migration-upgrade` → `seed-tenant` → `seed` → `smoke` |
| `make load-validate` | `load-smoke-thresholds` → `load-smoke-ready-thresholds` |
