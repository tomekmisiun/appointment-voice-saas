# ADR 0001: Sync vs Async API Architecture

- **Status:** Accepted (template guidance)
- **Date:** June 2026
- **Debt:** TD-012
- **Roadmap:** P2 #24

## Context

This template ships synchronous FastAPI route handlers (`def`) with sync
SQLAlchemy sessions and a Redis-backed worker queue. That choice keeps the
codebase approachable for forks and matches many internal CRUD APIs.

Under concurrent load, sync handlers occupy a worker thread until completion.
Login is CPU-bound (bcrypt) and database-bound (user lookup, token issuance).
Without enough Uvicorn workers or horizontal replicas, latency rises before
PostgreSQL saturates.

P2 #23 added `docs/architecture/scaling.md` and an `auth-login` load profile
so forks can measure single- vs multi-worker behavior locally.

## Decision Drivers

- Predictable debugging and test patterns for template consumers
- Low migration cost for forks cloning the repo today
- Acceptable throughput for moderate SaaS traffic with sized sync workers
- Need a clear fork decision path when login/admin traffic outgrows sync sizing

## Options Considered

### 1. Stay sync; scale with workers and replicas (recommended default)

- Increase Uvicorn `--workers` or run more API replicas behind a load balancer
- Size PostgreSQL pools using the formula in `docs/operations/deployment.md`
- Use `docs/architecture/scaling.md` to validate changes

**Pros:** No rewrite; aligns with current code and tests; fastest path to production.

**Cons:** Thread overhead; bcrypt still consumes CPU per worker; many open DB
connections at high replica counts.

### 2. Full async API (async SQLAlchemy 2.x + `async def` routes)

- Migrate DB session dependency, services, and routes to async
- Use async-compatible Redis and HTTP clients throughout

**Pros:** Better concurrency for I/O-bound endpoints; fewer threads per process.

**Cons:** Large rewrite; every fork must maintain async discipline; worker queue
and CLI paths remain sync unless duplicated; high regression risk for the
template itself.

### 3. Hybrid (async routes for hot paths only)

- Convert auth/login/register and other high-QPS endpoints first

**Pros:** Targets bottlenecks without full migration.

**Cons:** Two execution models in one codebase; harder to document and test;
easy for forks to drift into inconsistent patterns.

## Decision

**The template remains sync-first.** Production guidance is explicit multi-worker
or horizontal replica scaling with sized connection pools (P0 #3, P2 #23).

Forks that outgrow sync sizing should treat async migration as a **fork-owned
project**, not an upstream template change, unless a future major template
version commits to a full rewrite.

Recommended fork workflow:

1. Run sync benchmarks (`make load-smoke-auth-login-thresholds`, multi-worker
   steps in `docs/architecture/scaling.md`).
2. If login/admin p95 or throughput still miss SLO after worker/replica tuning,
   prototype async auth routes in the fork behind feature flags.
3. Re-evaluate full async only after measuring DB/Redis as the next bottleneck.

## Consequences

- **Template:** Keeps one clear execution model; CI and docs stay sync-oriented.
- **Forks with moderate traffic:** Scale workers/replicas; no async required.
- **Forks with heavy auth traffic:** Plan async auth or external auth service;
  budget a multi-sprint migration and new load tests.
- **TD-012:** Closed as guidance — benchmark + ADR satisfy the debt item; async
  rewrite is intentionally out of scope for the template baseline.

## References

- `docs/architecture/scaling.md`
- `docs/operations/deployment.md`
- `docs/operations/runbooks/production-runtime.md`
- `docs/archive/legacy/foundation-template-roadmap.md` P2 #23, P2 #24
