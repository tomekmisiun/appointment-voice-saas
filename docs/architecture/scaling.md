# Sync Route Scaling Benchmark

Guide for measuring how this template scales with multiple Uvicorn workers while
routes remain synchronous (`def`) and the auth path uses bcrypt password checks.

For the long-term async rewrite decision, see
`docs/adr/0001-sync-vs-async-architecture.md`.

## Why This Matters

Most API routes in this template are sync handlers backed by sync SQLAlchemy
sessions. Under concurrent load, each request occupies a worker thread until the
handler returns. Login is especially expensive because bcrypt verification is
CPU-bound.

Before horizontal scaling or async refactors, measure:

1. **Health baseline** — cheap control profile (`health`)
2. **Auth login path** — bcrypt + DB lookup profile (`auth-login`)

Compare single-worker vs multi-worker throughput on the same machine to validate
worker sizing and PostgreSQL pool headroom.

## Prerequisites

```bash
make docker-up
make migration-upgrade
make seed
```

The `auth-login` profile defaults to the dev seed account:

- email: `user@example.local`
- password: `devpassword123`

Override credentials when needed:

```bash
export LOAD_LOGIN_EMAIL=bench@example.local
export LOAD_LOGIN_PASSWORD='bench-password'
```

## Rate Limits During Auth Benchmarks

Login is rate-limited per client IP (`AUTH_LOGIN_RATE_LIMIT_*`). For meaningful
auth throughput measurements, temporarily raise the limit in `.env` for the
benchmark environment only:

```bash
AUTH_LOGIN_RATE_LIMIT_LIMIT=200
AUTH_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60
```

Restart the API after changing env values:

```bash
docker compose up -d --force-recreate api
```

Do not ship relaxed auth rate limits to production.

## Single-Worker Baseline

The default Compose API service runs single-process Uvicorn. Collect baselines:

```bash
make load-smoke-thresholds
make load-smoke-auth-login-thresholds
```

Save the JSON output from each run. Note `throughput_rps`, `p95_ms`, and
`p99_ms`.

## Multi-Worker Comparison

Override the API command to run multiple in-process workers. Example Compose
override file `docker-compose.benchmark.yml`:

```yaml
services:
  api:
    command:
      [
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--workers",
        "2",
      ]
```

Run the stack with the override:

```bash
docker compose -f docker-compose.yml -f docker-compose.benchmark.yml up -d --force-recreate api
```

Repeat both profiles and compare throughput. For CPU-bound login traffic, total
`throughput_rps` often scales roughly with worker count until another resource
saturates (PostgreSQL connections, Redis, or host CPU).

Return to the default single-worker API when finished:

```bash
docker compose up -d --force-recreate api
```

## Database Pool Headroom

Each worker maintains its own SQLAlchemy pool. Before increasing workers or API
replicas, verify PostgreSQL `max_connections` using the formula in
`docs/operations/deployment.md`:

```text
required_connections >= api_workers_or_replicas * (DB_POOL_SIZE + DB_MAX_OVERFLOW)
                       + worker_replicas * worker_pool
                       + admin/backup headroom
```

On startup the API logs effective pool settings via `log_db_pool_configuration()`.

## Profiles And Makefile Targets

Named profiles live in `perf/profiles.json`:

| Profile | Request | Default thresholds |
|---------|---------|-------------------|
| `health` | `GET /health` | `p95 <= 500ms`, `throughput >= 10 rps` |
| `health-ready` | `GET /health/ready` | `p95 <= 2000ms`, `throughput >= 5 rps` |
| `auth-login` | `POST /api/v1/auth/login` | `p95 <= 5000ms`, `throughput >= 2 rps` |

Makefile targets:

```bash
make load-smoke-auth-login
make load-smoke-auth-login-thresholds
```

Tune workload size:

```bash
LOAD_REQUESTS=40 LOAD_CONCURRENCY=8 make load-smoke-auth-login-thresholds
```

Threshold defaults are generous for local Docker. Tighten them after you record
a baseline on your target hardware.

## Interpreting Results

| Observation | Likely cause | Next step |
|-------------|--------------|-----------|
| Login throughput flat as workers increase | bcrypt CPU saturation on one core, or rate limits | Raise benchmark rate limits; compare host CPU; add workers/replicas |
| Health scales, login does not | Expected for CPU-bound auth on sync workers | Size workers for login SLO; plan async spike (ADR) |
| Throughput drops with more workers | DB pool or Postgres connection exhaustion | Lower workers or raise pool limits with DB capacity check |
| High `p95_ms` with low throughput | Thread pool or dependency latency | Inspect DB/Redis latency; review pool and worker counts |

## Related Docs

- `docs/testing/load-and-concurrency.md` — threshold runner and concurrency tests
- `docs/operations/deployment.md` — pool sizing and production runtime guidance
- `docs/operations/runbooks/production-runtime.md` — Gunicorn/Uvicorn worker examples
