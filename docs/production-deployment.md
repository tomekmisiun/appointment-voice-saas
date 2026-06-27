# Production Deployment Guide

This template is a reusable FastAPI backend foundation. It is not tied to one
business domain or one hosting provider. Adapt the deployment target to the
project, but keep the operational contract below.

> **VoxSlot deployment:** This project uses Railway. The active deployment
> flow (automatic Railway deploy after green CI on `main`) is documented in
> [`.github/DEPLOY.md`](../.github/DEPLOY.md). The generic manual
> workflow described below (`deploy.yml` + GHCR + SSH/hook promote) is
> retained as a template reference and emergency fallback.

## Supported Deployment Shape

The production runtime should provide these independently managed services:

- API process running the FastAPI application.
- Worker process running `python -m app.worker`.
- PostgreSQL database.
- Redis instance.
- S3-compatible object storage.
- SMTP or replaceable email delivery provider.
- Metrics, logs, and alerting stack.

The local Docker Compose files are development-oriented. Production can use
Kubernetes, a PaaS, container services, or Docker on a VM, but the deployment
must preserve the same process and dependency boundaries.

## Environments

Use separate environments for local development, staging, and production.

- `development`: local developer workflow with Docker Compose or uv.
- `test`: automated tests and CI.
- `staging`: production-like validation before release.
- `production`: real traffic and real customer data.

Required expectations:

- Staging and production use separate databases, Redis instances, buckets, and
  email credentials.
- Staging should run the same image version that will be promoted to
  production.
- Production must set `ENVIRONMENT=production`.
- Production secrets must not come from committed files.
- Production deploys must not mount the source tree into the runtime container.

## Secrets

Use a real secret manager or deployment-platform secret store for production.
Examples include cloud secret managers, Kubernetes Secrets backed by sealed or
external secrets, or a PaaS secret store.

Production secrets include:

- `SECRET_KEY`
- database URL and credentials
- Redis credentials if required by the provider
- SMTP credentials
- S3 access keys
- Grafana and observability credentials

Rules:

- Never commit `.env` files with real values.
- Rotate secrets through the deployment platform, not through code changes.
- Keep a documented emergency rotation procedure for `SECRET_KEY`, database
  credentials, S3 credentials, and email credentials.
- Treat `SECRET_KEY` rotation as a breaking session/token event unless a
  key-ring strategy is added in the future.

## Deployment Flow

Use this flow for normal releases:

1. Merge feature branches into `main` with a non-fast-forward merge commit.
2. Ensure CI passes on `main`.
3. Build a deployable image from the merge commit SHA.
4. Tag the image with the commit SHA and, if useful, a release tag.
5. Deploy the image to staging.
6. Run staging migrations with `alembic upgrade head`.
7. Run smoke checks in staging:
   - `GET /health/live`
   - `GET /health/ready`
   - `GET /metrics`
   - login or another authenticated smoke path
   - worker startup and queue connectivity
8. Promote the same image to production.
9. Run production migrations according to the migration strategy.
10. Shift traffic to the new API process.
11. Verify production health, metrics, logs, and worker status.
12. Keep the previous image available until the release is accepted.

## Migration Strategy

Alembic migrations are required for every database schema change.

Default migration order:

1. Backup or confirm a recent restorable backup exists.
2. Deploy code that is compatible with both the old and new schema when
   possible.
3. Run `alembic upgrade head`.
4. Verify readiness and application smoke checks.
5. Remove old compatibility code in a later release when needed.

For risky changes, prefer expand/contract migrations:

- First release: add nullable columns, new tables, or backward-compatible
  indexes.
- Backfill data separately when needed.
- Second release: switch reads/writes to the new shape.
- Later release: drop old columns or constraints.

Do not make destructive migrations without an explicit rollback and restore
plan.

## Rollback Strategy

Application rollback:

- Keep the previous production image tag available.
- Roll back to the previous image when the new release fails before or after
  traffic shift.
- Verify `GET /health/ready`, logs, metrics, and core auth flow after rollback.

Database rollback:

- Prefer forward-fix migrations over down migrations for production incidents.
- Use database restore only when data corruption or destructive schema changes
  require it.
- Test restore procedures outside production before relying on them.

Rollback checklist:

- Identify whether the incident is app-only, schema-related, data-related, or
  dependency-related.
- Stop or pause affected workers if they may worsen data state.
- Roll back app image or deploy a forward fix.
- Confirm database compatibility.
- Verify health checks and key user flows.
- Document the incident and follow-up actions.

## Backup And Restore

Production PostgreSQL must have automated backups. The exact mechanism depends
on the hosting provider, but the project using this template should document:

- backup frequency
- retention period
- encryption at rest
- restore target
- recovery point objective
- recovery time objective
- restore rehearsal cadence

Minimum expectation:

- daily backups for non-critical projects
- more frequent backups for SaaS projects with customer data
- a restore rehearsal before first production launch
- periodic restore rehearsals after launch

Object storage should also have a retention and deletion policy. If uploaded
files are business-critical, verify that bucket versioning or equivalent
recovery exists.

## Health And Smoke Checks

Use these endpoints in deployment automation:

- `GET /health/live` for process liveness.
- `GET /health/ready` before receiving traffic.
- `GET /health/db` when debugging database connectivity.
- `GET /health/redis` when debugging Redis connectivity.
- `GET /metrics` for Prometheus scraping.

Readiness must pass before a new API instance receives traffic.

## Runtime Hardening

Configure production runtime behavior through environment variables instead of
code changes.

Database pool settings:

- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `DB_POOL_RECYCLE_SECONDS`
- `DB_POOL_PRE_PING`
- `DB_POOL_TIMEOUT_SECONDS`
- `DB_STATEMENT_TIMEOUT_MS`

Each API process opens at most `DB_POOL_SIZE + DB_MAX_OVERFLOW` PostgreSQL
connections. The API logs the effective values at startup (`db_pool_configured`
in application logs).

Size PostgreSQL `max_connections` with:

```text
required_connections >= api_workers_or_replicas * (DB_POOL_SIZE + DB_MAX_OVERFLOW)
                       + worker_replicas * worker_pool
                       + admin/backup headroom
```

Example: `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=10`, two Uvicorn workers, and two
API replicas need up to `2 * 2 * 15 = 60` API connections before workers and
headroom.

For sync route handlers, prefer explicit multi-worker or horizontal replica
scaling with a sized pool. See `docs/production-runtime-examples.md` for Gunicorn
and Uvicorn worker examples.

Redis production connectivity:

- `REDIS_USERNAME`
- `REDIS_PASSWORD`
- `REDIS_SSL`
- `REDIS_SSL_CERT_REQS`
- `REDIS_SOCKET_TIMEOUT_SECONDS`
- `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS`

See `docs/redis-production-contract.md` for HA expectations, feature-level
fail-closed behavior (especially refresh rotation), and operational checks.

Production validation requires a non-local `REDIS_HOST`, a non-empty
`REDIS_PASSWORD`, and explicit trusted host configuration.

HTTP hardening:

- `SECURITY_HEADERS_ENABLED`
- `HSTS_ENABLED`
- `HSTS_MAX_AGE_SECONDS`
- `CORS_ENABLED`
- `CORS_ALLOW_ORIGINS`
- `CORS_ALLOW_CREDENTIALS`
- `CORS_ALLOW_METHODS`
- `CORS_ALLOW_HEADERS`
- `TRUSTED_HOSTS_ENABLED`
- `TRUSTED_HOSTS`

Production validation requires `TRUSTED_HOSTS_ENABLED=true`, a non-empty
`TRUSTED_HOSTS` list, disallows wildcard CORS origins, and requires
`RATE_LIMIT_TRUST_FORWARDED_HEADERS=true` so auth rate limits key on the
original client IP behind a reverse proxy.

Recommended API process settings behind a reverse proxy or load balancer:

- run Uvicorn with multiple workers only when the deployment platform expects
  in-process workers; otherwise scale API replicas horizontally
- terminate TLS at the load balancer or ingress
- enable `HSTS_ENABLED=true` only when HTTPS is enforced end-to-end for clients
- keep development-only bind mounts and reload mode out of production
- use `ENVIRONMENT=production` and JSON logs in production when logs are shipped
  to a central system

Example production Uvicorn command:

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --proxy-headers \
  --forwarded-allow-ips='*'
```

Adjust worker count, proxy header trust, and forwarded IP allowlists to match
the hosting platform.

## Container Images

The `Dockerfile` defines two build targets:

- `development`: installs runtime and dev/test dependencies for local Compose,
  pytest, Ruff, and pre-commit workflows.
- `production`: installs runtime dependencies only and uses a production-oriented
  Uvicorn entrypoint with `--proxy-headers`.

Build the production image:

```bash
docker build --target production -t fastapi-production-foundation-api:production .
```

Local Docker Compose explicitly builds the `development` target for `api` and
`worker`. Release and CI image builds use the `production` target.

Production containers should run the image entrypoint without bind mounts,
without dev dependency groups, and with environment variables supplied by the
deployment platform.

## GitHub Actions Deployment Workflow

The repository includes a manual `deploy.yml` workflow for staging and
production promotion. It supports three deployment backends:

- `DEPLOY_HOOK_URL`: POST a JSON payload with the target environment, image
  reference, and migration flag to your platform deploy hook.
- `DEPLOY_SSH_HOST`: run `docker-compose.prod.yml` on a remote host through SSH.
- Dry run mode: validate inputs and print the promotion plan without applying
  changes.

Configure separate GitHub environments named `staging` and `production`. Each
environment can define its own secrets and variables.

Common environment variables:

- `API_BASE_URL`: base URL used by post-deploy smoke checks.
- `REMOTE_APP_DIR`: remote directory containing `docker-compose.prod.yml` for
  SSH deployments.
- `SMOKE_ADMIN_EMAIL`: smoke-test login email.
- `ALLOW_LATEST_PRODUCTION`: set to `true` only if production may deploy the
  `latest` tag.

Common environment secrets:

- `DEPLOY_HOOK_URL`
- `DEPLOY_HOOK_TOKEN`
- `DEPLOY_SSH_HOST`
- `DEPLOY_SSH_USER`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DATABASE_URL`: optional runner-side Alembic execution after hook/SSH promotion.
- `SMOKE_ADMIN_PASSWORD`

Recommended promotion flow:

1. Publish a release image to GHCR from `release.yml`.
2. Run `Deploy` in GitHub Actions with `dry_run=true` first.
3. Run the workflow again with `dry_run=false` for the target environment.
4. Confirm smoke checks pass against `API_BASE_URL`.

For VM-style deployments, copy `docker-compose.prod.yml` and a production `.env`
file to the remote host, then configure SSH deployment secrets and
`REMOTE_APP_DIR`. See `docs/production-runtime-examples.md` for reverse-proxy
examples (Nginx, Caddy, Traefik) and the GitHub environment checklist.

Local dry run:

```bash
make deploy-dry-run ENVIRONMENT=staging IMAGE_TAG=1.2.3
```

Recommended post-deploy smoke checks:

- register/login or a project-specific auth flow
- authenticated `GET /auth/me`
- worker can connect to Redis
- API can connect to object storage if file uploads are enabled
- logs and metrics are visible

## Operational Ownership

Before using this template for a real project, define:

- deployment platform
- production domain and TLS termination
- secret manager
- backup provider and restore process
- alert destinations
- incident owner
- rollback owner
- database migration owner
- expected service-level indicators

## Current Template Limits

This guide defines the production operating model, but the repository still
does not include provider-specific infrastructure as code, alert rules, error
tracking, tracing, or automated backup/restore verification. The GitHub Actions
deploy workflow is executable, but each project must still configure its own
deployment backend, secrets, and hosting platform.
