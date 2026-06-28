# Deployment

The active production path is Railway through GitHub Actions. Self-managed
Docker Compose examples exist, but they are not the primary deployment path.

## Supported Production Shape

| Service | Configuration |
|---|---|
| API | [`railway.api.toml`](../../railway.api.toml), Dockerfile `production` target. |
| Worker | [`railway.worker.toml`](../../railway.worker.toml), starts `python -m app.worker`. |
| Frontend | [`frontend/railway.toml`](../../frontend/railway.toml), Railpack build. |
| PostgreSQL | Managed Railway plugin or equivalent external PostgreSQL. |
| Redis | Managed Railway plugin or equivalent external Redis. |
| Object storage | S3-compatible provider; MinIO is local-only unless explicitly deployed. |

## Automatic Production Deploy

`.github/workflows/ci.yml` deploys to Railway on pushes to `main` after the CI
gate passes. The deploy job:

1. Installs the Railway CLI.
2. Validates `RAILWAY_TOKEN`.
3. Deploys API with `railway.api.toml`.
4. Deploys worker with `railway.worker.toml`.
5. Deploys frontend with `frontend/railway.toml`.

`railway.api.toml` defines:

- production Docker build target,
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers`,
- `/health/live` health check,
- pre-deploy command: `alembic upgrade head && python -m app.seed_demo_data`.

## Manual Promotion Workflow

`.github/workflows/deploy.yml` is a manually dispatched image-promotion workflow.
It resolves a GHCR image tag, can dry-run, can run migrations, and can run
smoke checks when the required environment variables/secrets are configured.

Do not treat this workflow as the automatic Railway path; it is a separate
operator-controlled promotion path.

## Local Docker Development

Use the local Compose stack for development:

```bash
cp .env.example .env
make docker-up
make migration-upgrade
make seed-demo
```

Local services are defined in [`docker-compose.yml`](../../docker-compose.yml):
API, worker, PostgreSQL, test PostgreSQL, Redis, and MinIO.

## Self-Managed Container Manifest

[`docker-compose.prod.yml`](../../docker-compose.prod.yml) contains only API and
worker containers. It does not include PostgreSQL, Redis, object storage, TLS,
or migrations. Use it only as a minimal runtime example with external managed
dependencies.

See [`production-runtime-examples.md`](runbooks/production-runtime.md) for
optional Nginx/Caddy/Traefik and multi-worker examples.

## Health And Smoke Checks

| Check | Endpoint/command |
|---|---|
| API live | `/health/live` |
| API ready | `/health/ready` |
| Metrics | `/metrics` |
| Local smoke | `make smoke` |
| Load smoke | `make load-smoke-ci` |

The current technical debt register notes that production post-deploy smoke is
not yet an enforced CI gate.

## Production Status Boundary

Current readiness is tracked in [`CURRENT_STATE.md`](../project/current-state.md). Do not
mark the project production-ready until the active blockers in
[`../TECH_DEBT.md`](../../TECH_DEBT.md) are resolved and verified.

