# Redis Production Contract

This document defines how production deployments must treat Redis in this
template. Redis is a **hard runtime dependency** for API and worker processes.
There is no supported degraded mode where the application continues serving
traffic without Redis.

Resilience code changes (circuit breakers, clearer error surfaces) are tracked
separately in ROADMAP P1 #14 (`TD-004` implementation).

## Hard Dependency

Both the API and worker require a reachable Redis instance at startup and during
normal operation. Readiness checks call `PING` (`app/services/health_service.py`).
If Redis is unavailable:

- `/health/ready` fails and orchestrators should stop routing traffic.
- Auth refresh rotation, rate limits, caching, idempotency locks, and the job
  queue cannot operate correctly.

Production validation already rejects local Docker/loopback Redis hosts and
requires a non-empty `REDIS_PASSWORD` (`app/core/config.py`). See
`docs/operations/deployment.md` for connectivity settings (`REDIS_SSL`,
timeouts, and related variables).

## Feature Matrix

| Feature | Redis usage | Failure posture today |
|---------|-------------|---------------------|
| Refresh token rotation | `SET` with `NX` on `revoked_refresh_token:{jti}` (`app/core/redis.py`) | **Fail-closed** — rotation returns `401` when the token was already rotated; Redis errors surface as request failures instead of issuing duplicate refresh tokens |
| Refresh token revocation check | `EXISTS` on revoked keys | **Fail-closed** — refresh requests fail rather than accepting tokens that cannot be checked |
| Logout | `SET` revoked key | Best-effort revoke; Redis errors propagate |
| User list cache | get/set/delete (`app/core/cache.py`) | **Degraded** — cache helpers swallow Redis errors; requests fall back to PostgreSQL |
| Auth and ingress rate limits | `INCR` + `EXPIRE` (`app/api/dependencies/rate_limit.py`) | **Fail-closed** — returns `503 Service temporarily unavailable` when counters cannot be updated |
| Idempotency locks | short-lived `SET`/`DELETE` (`app/services/idempotency_service.py`) | **Fail-closed** for mutating endpoints that require idempotency |
| Worker job queue | lists, delayed queue, processing queue, failed queue (`app/core/job_queue.py`) | **Fail-closed** — workers cannot dequeue, ack, or retry jobs |
| Worker maintenance lock | `SET` with TTL (`app/core/job_queue.py`) | Maintenance skipped when lock cannot be acquired |
| Password-reset job idempotency marker | `SET`/`EXISTS` (`app/services/password_reset_service.py`) | Worker retries may duplicate side effects if Redis is down during marker write |

Treat any row marked **fail-closed** as a production incident when Redis is
unavailable. Do not expect graceful auth or queue progress during an outage.

## Refresh Rotation Fail-Closed Behavior

`/auth/refresh` calls `rotate_refresh_token()` (`app/services/auth_service.py`):

1. Decode and validate the presented refresh JWT.
2. Atomically mark the old refresh `jti` as revoked with `SET ... NX` and a TTL
   matching token expiry.
3. Issue a new access token and refresh token only when step 2 succeeds.

If the `jti` was already revoked (replay or concurrent refresh), the handler
returns `401` with `Refresh token has been revoked`. This prevents two valid
refresh tokens after rotation.

If Redis cannot execute the atomic `SET NX` (network partition, primary
failover, or outage), the refresh request fails instead of silently skipping
rotation bookkeeping. Operators should monitor Redis availability alongside
`/health/ready` and auth error rates.

## High Availability Requirements

Production Redis must be operated for availability, not as a single container
with no failover plan.

Minimum expectations for teams adopting this template:

- **Managed Redis** (ElastiCache, Memorystore, Azure Cache, etc.) with automatic
  failover, or self-managed Redis Sentinel / Cluster with documented failover
  runbooks.
- **Separate Redis per environment** (development, staging, production) with
  isolated credentials.
- **TLS in transit** where the provider supports it (`REDIS_SSL=true`,
  `REDIS_SSL_CERT_REQS=required` in production when connecting over public
  networks).
- **Password authentication** enabled (`REDIS_PASSWORD` required in production
  validation).
- **Monitoring and alerting** on memory usage, evictions, replication lag,
  connection count, and command latency.
- **Backup / restore policy** if you store data that must survive catastrophic
  failure. This template uses Redis primarily for ephemeral state (queues,
  rate-limit counters, revocation markers, cache). Plan RPO/RTO accordingly; most
  keys are safe to lose briefly except in-flight queue jobs and active rate-limit
  windows.

Sizing guidance:

- Provision enough memory for peak queue depth, rate-limit key cardinality, and
  cache working set.
- Avoid `allkeys-lru` eviction without understanding impact: evicting queue or
  revocation keys can cause subtle auth and worker failures.
- Keep API and worker processes in the same network segment as Redis with low
  latency; tune `REDIS_SOCKET_TIMEOUT_SECONDS` and
  `REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS` for your topology.

## Operational Checks

Before go-live:

1. Confirm `/health/ready` includes Redis (`GET /health/redis` for targeted
   checks).
2. Run a refresh rotation smoke test against staging Redis.
3. Verify worker dequeue/ack against the same Redis endpoint used by the API
   job enqueue paths.
4. Document on-call steps for Redis failover (see `docs/operations/troubleshooting.md`).

## Related Documents

- `docs/operations/deployment.md` — production env vars and validation
- `docs/operations/troubleshooting.md` — local and staging Redis connectivity issues
- `docs/archive/legacy/foundation-template-roadmap.md` P1 #14 — Redis resilience implementation (`TD-004`)
