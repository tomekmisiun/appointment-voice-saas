# Load and Concurrency Testing

Lightweight local performance thresholds and concurrency regression coverage for
critical infrastructure paths.

## Purpose

This template ships two complementary layers:

1. **Load thresholds** via `perf/load_baseline.py` and `perf/thresholds.py`
2. **Concurrency regression tests** in `tests/test_concurrency.py`

Together they provide repeatable local checks for latency, throughput, and race
conditions across idempotency, workers, auth/session rotation, Redis, storage,
and slow dependency paths.

## Load Thresholds

Start the stack:

```bash
make docker-up
```

Run the default health profile with threshold enforcement:

```bash
make load-smoke-thresholds
```

Run the readiness profile, which includes database and Redis checks:

```bash
make load-smoke-ready-thresholds
```

Run both profiles:

```bash
make load-validate
```

Run the bcrypt/login profile (requires dev seed and relaxed auth rate limits for
larger workloads — see `docs/architecture/scaling.md`):

```bash
make load-smoke-auth-login-thresholds
```

Override workload size or thresholds when needed:

```bash
LOAD_REQUESTS=100 LOAD_CONCURRENCY=10 make load-smoke-thresholds
LOAD_MAX_P95_MS=750 make load-smoke-ready-thresholds
```

Profiles live in `perf/profiles.json`:

| Profile | Path | Default thresholds |
|---------|------|--------------------|
| `health` | `/health` | `p95 <= 500ms`, `throughput >= 10 rps` |
| `health-ready` | `/health/ready` | `p95 <= 2000ms`, `throughput >= 5 rps` |
| `auth-login` | `POST /api/v1/auth/login` | `p95 <= 5000ms`, `throughput >= 2 rps` |

The script exits with status `1` when thresholds fail.

## Result Format

When `--check-thresholds` is enabled, the script prints:

```json
{
  "summary": {
    "target": "http://api:8000/health",
    "count": 50,
    "throughput_rps": 59.52,
    "p95_ms": 11.36
  },
  "thresholds": {
    "max_p95_ms": 500,
    "min_throughput_rps": 10
  },
  "threshold_violations": [],
  "passed": true
}
```

## Concurrency Coverage

`tests/test_concurrency.py` covers:

- exclusive idempotency lock acquisition
- single persisted idempotency record under concurrent writes
- single successful refresh-token rotation under concurrent reuse
- exclusive refresh-token revocation claims
- one dequeue per queued worker job
- Redis rate-limit counter behavior under concurrent increments
- unique upload object keys under concurrent generation
- readiness checks under artificially slow dependency latency

Run the suite with the standard validation workflow:

```bash
make validate
```

## CI And Manual Load Workflows

Pull requests run a lightweight load threshold smoke check in `.github/workflows/ci.yml`
(`load-smoke` job) against the `health` profile with reduced request volume.

Use `.github/workflows/load-threshold.yml` to run full threshold checks manually
(`health` or `health-ready`) when you want deeper post-merge performance
verification outside the default PR smoke job.

## Notes

- Threshold defaults are intentionally generous for local Docker environments.
- Downstream projects should tighten profiles for their hosting target.
- Load thresholds complement, but do not replace, dedicated load-testing tools
  such as k6 or Locust for large-scale capacity planning.
- Multi-worker sync scaling benchmarks and login load profiles:
  `docs/architecture/scaling.md`.
