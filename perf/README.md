# Load Baseline

Lightweight local performance smoke for the API template.

## Purpose

`load_baseline.py` measures request latency and throughput for a single HTTP
endpoint. It is intended for local regression checks before larger load-testing
work in downstream projects.

Repeatable thresholds are available through named profiles in
`perf/profiles.json` and the threshold helpers in `perf/thresholds.py`.

## Run

Start the stack first:

```bash
make docker-up
```

Run the baseline against the API service from inside Docker:

```bash
make load-smoke
```

Run threshold-enforced profiles:

```bash
make load-smoke-thresholds
make load-smoke-ready-thresholds
make load-validate
make load-smoke-auth-login-thresholds
```

Override defaults when needed:

```bash
API_BASE_URL=http://api:8000 LOAD_REQUESTS=100 LOAD_CONCURRENCY=10 make load-smoke
```

Include database and Redis dependency latency by targeting readiness:

```bash
docker compose run --rm api python -m perf.load_baseline \
  --base-url http://api:8000 \
  --path /health/ready \
  --requests 50 \
  --concurrency 5
```

Use a named profile with threshold enforcement:

```bash
docker compose run --rm api python -m perf.load_baseline \
  --base-url http://api:8000 \
  --profile health-ready \
  --check-thresholds
```

## Result format

The script prints JSON with:

- `target`: requested URL
- `count`: completed requests
- `total_seconds`: wall-clock runtime
- `throughput_rps`: requests per second
- `min_ms`, `max_ms`, `mean_ms`
- `p50_ms`, `p95_ms`, `p99_ms`

When `--check-thresholds` is enabled, the payload also includes:

- `summary`: latency and throughput metrics
- `thresholds`: active threshold values
- `threshold_violations`: list of failed checks
- `passed`: boolean result

Example:

```json
{
  "summary": {
    "target": "http://api:8000/health",
    "count": 50,
    "total_seconds": 0.84,
    "throughput_rps": 59.52,
    "min_ms": 1.42,
    "max_ms": 18.77,
    "mean_ms": 4.91,
    "p50_ms": 4.12,
    "p95_ms": 11.36,
    "p99_ms": 18.77
  },
  "thresholds": {
    "max_p95_ms": 500,
    "min_throughput_rps": 10
  },
  "threshold_violations": [],
  "passed": true
}
```

Record results in project notes or CI artifacts when comparing changes over
time. Default profile thresholds are generous for local Docker environments.
Tighten them for your hosting target.

Named profiles in `perf/profiles.json`:

| Profile | Request | Default thresholds |
|---------|---------|-------------------|
| `health` | `GET /health` | `p95 <= 500ms`, `throughput >= 10 rps` |
| `health-ready` | `GET /health/ready` | `p95 <= 2000ms`, `throughput >= 5 rps` |
| `auth-login` | `POST /api/v1/auth/login` | `p95 <= 5000ms`, `throughput >= 2 rps` |

Multi-worker sync scaling benchmarks: `docs/architecture/scaling.md`.

See `docs/testing/load-and-concurrency.md` for concurrency regression coverage and
the manual GitHub Actions workflow.
