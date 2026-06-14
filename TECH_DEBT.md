# Technical Debt Register

Identified from the June 2026 production audits (implementation review only).
Each item is an open engineering debt unless marked **Done** with code verification.

For prioritized remediation order, see `ROADMAP.md`.  
For verified current capabilities, see `PROJECT_STATUS.md`.

**Status legend:** Open | In Progress | Done

---

## Critical

| ID | Issue | Impact | Recommendation | Effort | Status |
|----|-------|--------|----------------|--------|--------|
| TD-001 | Production Docker image runs single-process Uvicorn (`Dockerfile` CMD, no `--workers`). | One CPU core serves all traffic; auth path saturates under login spikes. | Document multi-worker/replica scaling and require production CMD override when needed (`docs/production-runtime-examples.md`); horizontal scaling remains operator responsibility. | M | Done |
| TD-002 | Legacy API router remounts auth/users/admin/tenants/files at unversioned paths (`app/api/legacy.py`, `app/main.py`). | Doubles protected attack surface; forks forget to remove deprecated routes. | Gate behind env flag (default off in production) or remove in next major version. | S | Done |
| TD-003 | Worker processing queue has no visibility timeout or reaper (`brpoplpush` in `app/core/job_queue.py`). | Worker crash/OOM during deploy leaves jobs stuck in `app_jobs_processing` forever. | Add stale-job reclaim (visibility timeout, heartbeat, or periodic reaper). | M | Done |
| TD-004 | Hard dependency on Redis with no degradation policy (rate limits, refresh rotation, cache, idempotency locks, job queue). | Redis blip causes auth failures, 429/500 cascades, and queue stall across the system. | Production contract in `docs/redis-production-contract.md`; cache degrades gracefully; rate limits return `503` when Redis is unavailable. | L | Done |

---

## High

| ID | Issue | Impact | Recommendation | Effort | Status |
|----|-------|--------|----------------|--------|--------|
| TD-005 | `/metrics` is unauthenticated (`app/api/routes/metrics.py`). | Traffic patterns and dependency health leak if exposed beyond internal network. | Restrict via network ACL, mTLS, or auth middleware; document requirement. | S | Done |
| TD-006 | Rate limits key on `request.client.host` only (`app/api/dependencies/rate_limit.py`). | Behind reverse proxy: limits are ineffective or block all users on one IP. | Parse trusted forwarded headers; align with Uvicorn `--proxy-headers` and allowlist. | M | Done |
| TD-007 | JWT encode uses hardcoded `ALGORITHM`; decode uses `settings.algorithm` (`app/core/security.py`). | Misconfigured env breaks auth or creates inconsistent token validation. | Single source of truth for signing algorithm. | S | Done |
| TD-008 | `UserAdminUpdate.role` accepts arbitrary strings (`app/schemas/user.py`). | Invalid roles get empty permissions or accidental lockout. | Validate against allowed role enum in schema/service. | S | Done |
| TD-009 | Malware scanning disabled by default; fallback scanner checks filename only (`app/core/config.py`, `app/services/malware_scanner.py`). | Malicious uploads stored if forks enable files without wiring a scanner. | Fail production startup when uploads enabled without real scanner URL. | S | Done |
| TD-010 | Idempotency records expire logically but are never deleted (`app/services/idempotency_service.py`). | Table bloat slows lookups and increases backup/storage cost. | Scheduled purge of rows where `expires_at < now()`. | S | Done |
| TD-011 | Unknown worker job types log a warning then are acknowledged (`app/worker.py`). | Schema drift or typos silently drop jobs. | Route unknown types to DLQ instead of ack. | S | Done |
| TD-012 | Nearly all routes are sync `def` with sync SQLAlchemy sessions. | Thread pool exhaustion under concurrent DB-bound load before DB maxes out. | Async SQLAlchemy + async routes, or explicit multi-worker sync sizing. | XL | Done |
| TD-013 | Default DB pool (`pool_size=5`, `max_overflow=10`) with no startup visibility. | Naive horizontal scaling exhausts Postgres `max_connections`. | Log effective pool; document `(workers × replicas × pool)` formula. | S | Done |
| TD-014 | Refresh tokens omit `token_version` (`app/core/security.py`). | Compromised refresh remains valid until rotation after role change/password reset. | Embed and validate `token_version` on refresh. | M | Done |
| TD-015 | `/auth/refresh` and `/auth/logout` have no rate limits (`app/api/routes/auth.py`). | Refresh grinding amplifies Redis and DB load. | Add per-IP and per-token-hash limits. | S | Done |

---

## Medium

| ID | Issue | Impact | Recommendation | Effort | Status |
|----|-------|--------|----------------|--------|--------|
| TD-016 | No Docker `HEALTHCHECK` or compose healthchecks. | Orchestrators route traffic to hung containers; slow incident detection. | Add healthcheck hitting `/health/live`; wire compose conditions. | S | Done |
| TD-017 | No graceful shutdown for API or worker (`app/worker.py`, `app/main.py`). | Deployments drop in-flight work; jobs remain in processing queue. | SIGTERM handlers, drain timeout, FastAPI lifespan hooks. | M | Done |
| TD-018 | Python 3.14 base image (`Dockerfile`). | Hosting/ecosystem lag across hundreds of forks. | Pin to 3.12/3.13 LTS unless 3.14 is intentional. | S | Done |
| TD-019 | Webhook ingress has no rate limit or max body size (`app/api/routes/webhooks.py`). | DoS via large payloads or high request volume. | Body size middleware; rate limit by provider/IP. | S | Done |
| TD-020 | No global handler for unhandled exceptions (`app/main.py`). | Possible internal detail leakage depending on debug settings. | Generic 500 handler; enforce `debug=False` in production docs. | S | Done |
| TD-021 | Tenant isolation is application-layer only (no PostgreSQL RLS). | Raw SQL or ORM bypass in forks can cross tenants. | Document requirement; optional RLS migration example. | L | Open |
| TD-022 | Password-reset worker idempotency marker set after DB commit (`app/services/password_reset_service.py`). | Crash between commit and Redis SET can duplicate tokens/emails on retry. | DB-level idempotency keyed by `job_id` or reorder side effects. | M | Done |
| TD-023 | Worker Prometheus metrics not scrapeable in default prod layout (metrics HTTP on API only). | Silent worker/backlog failures in operations. | Sidecar exporter, pushgateway, or shared `PROMETHEUS_MULTIPROC_DIR`. | M | Done |
| TD-024 | `webhook_events` table is insert-only with no retention (`app/services/webhook_service.py`). | Storage and query cost grow unbounded on high-volume forks. | Retention job and archival policy. | S | Done |
| TD-025 | Audit logs are append-only with no retention (`app/services/audit_log_service.py`). | Admin queries slow; compliance storage grows. | Scheduled purge by `created_at` retention window. | M | Done |
| TD-026 | User list used offset pagination for default admin queries (`app/api/routes/users.py`). | Deep pages become expensive at large tenant sizes. | Keyset/cursor pagination with legacy offset fallback. | M | Done |
| TD-027 | User email search used unindexed `%term%` ILIKE by default (`app/services/user_service.py`). | Sequential scans under admin search load. | Prefix search by default; optional contains mode with pg_trgm GIN index. | M | Done |
| TD-028 | User list cache invalidation uses Redis `SCAN` + bulk delete (`app/core/cache.py`). | Redis CPU spikes under high admin write churn. | Versioned cache keys or tag-based invalidation. | M | Done |
| TD-029 | New boto3 S3 client created per request (`get_storage_service()` in `app/services/storage_service.py`). | Connection overhead on file endpoints under concurrency. | Lifespan-cached or module-level client. | S | Done |
| TD-030 | Direct uploads buffer entire file in memory (`read_upload_body_limited`). | Memory spikes with concurrent max-size uploads. | Stream to S3 multipart upload. | M | Done |
| TD-031 | Presigned upload complete re-downloads object from S3 for sniff/scan. | 2× bandwidth; API acts as proxy at scale. | Scan at bucket edge or async worker. | M | Done |
| TD-032 | Readiness checks DB and Redis only, not S3 (`app/api/routes/health.py`). | Load balancer marks ready while uploads fail at runtime. | Optional S3 head-bucket in readiness when file features enabled. | S | Done |
| TD-033 | User update and audit log are separate DB commits (`app/api/routes/users.py`). | User changed without audit row on partial failure. | Single transaction or outbox pattern. | M | Done |
| TD-034 | Tenant `ContextVar` tokens stored but never reset (`app/api/dependencies/tenant.py`). | Stale tenant context under thread-reuse edge cases. | Clear tenant context at request entry in middleware. | S | Done |
| TD-035 | CI `docker-build` job does not depend on `test` (`.github/workflows/ci.yml`). | Image can pass Trivy while tests fail on same commit. | Add `needs: [test]`. | S | Done |
| TD-036 | Scheduled backup workflow exits successfully when secrets are missing. | False confidence that backups run. | Fail cron when required secrets absent. | S | Done |
| TD-037 | Observability docs reference missing assets (`.env.observability.example`, Grafana Prometheus datasource, dashboards). | Hundreds of clones waste time on broken local observability setup. | Add files or remove incorrect README/PROJECT_STATUS claims. | M | Done |
| TD-038 | Promtail config hardcodes Docker container name (`observability/promtail/promtail.yml`). | Log collection fails after compose project rename. | Use compose service discovery labels. | S | Done |
| TD-039 | Tenant `default` was seeded with fixed `id=1` in migration (`a1b2c3d4e5f6`). | Migration/assumption conflicts in multi-environment clones. | App seed command plus slug-based backfill without hardcoded tenant id. | M | Done |
| TD-040 | `platform_admin` is a tenant-bound user row, not a separate operator model. | Every fork re-implements operator/security model. | Separate operator table or explicit demo-only documentation. | L | Done |
| TD-041 | Services raised `HTTPException` directly throughout service layer. | Hard to reuse from workers/CLI; inconsistent error handling in forks. | Domain exceptions translated at route boundary. | L | Done |
| TD-042 | Worker loop runs maintenance and `promote_delayed_jobs` on every iteration. | Redis overhead under high queue depth. | Separate maintenance ticker; batch promote with limits. | S | Done |
| TD-043 | Possible double migration on deploy (SSH script + runner `deploy_migrate.sh`). | Redundant Alembic runs confuse runbooks. | Deduplicate migration step in deploy workflow. | S | Done |
| TD-044 | `release.yml` publishes `latest` tag while production deploy discourages it. | Easy misuse of mutable tag in production. | Document tension or stop tagging `latest`. | S | Done |
| TD-045 | `BaseHTTPMiddleware` used for request logging (`app/core/middleware.py`). | Extra latency under high load (known Starlette overhead). | Pure ASGI middleware. | M | Done |
| TD-046 | JWT access/refresh TTLs hardcoded (30 min / 7 days). | Product policy changes require code edits across forks. | Env-driven TTL settings. | S | Done |
| TD-047 | Duplicate `UserRead` schema in `app/schemas/auth.py` and `app/schemas/user.py`. | API contract drift risk. | Consolidate to single schema module. | S | Done |
| TD-048 | Alertmanager receiver is empty stub (`observability/alertmanager/alertmanager.yml`). | Local alerts go nowhere; forks assume routing works. | Document as stub; provide example receiver config. | S | Done |

---

## Low

| ID | Issue | Impact | Recommendation | Effort | Status |
|----|-------|--------|----------------|--------|--------|
| TD-049 | No `Content-Security-Policy` header (API-only template). | Minor for JSON APIs; relevant if HTML error pages served. | Add CSP when serving HTML. | S | Open |
| TD-050 | No OpenTelemetry integration. | Limited distributed tracing beyond optional Sentry. | Document as downstream choice or add optional OTel hook. | L | Open |
| TD-051 | No adversarial security test suite (JWT tampering, upload fuzzing). | Regressions in security controls may slip through. | Add targeted security regression tests. | M | Open |
| TD-052 | No end-to-end Docker test for api+worker+redis email flow. | Worker integration bugs found only in production. | Compose-based integration test in CI. | M | Open |
| TD-053 | Deploy/smoke scripts (`smoke_test.sh`, `deploy_remote_compose.sh`) lack unit tests. | Script regressions undetected until manual deploy. | Add script dry-run tests. | S | Open |
| TD-054 | Observability stack not validated in CI. | Broken Prometheus/alert rules merge unnoticed. | Optional CI job to lint prom rules / compose config. | M | Open |
| TD-055 | Migration tests cover one-step downgrade only. | Multi-revision rollback scenarios untested. | Extend migration rehearsal tests. | M | Open |
| TD-056 | Low coverage in `email_service.py`, `storage_service.py`, `db/session.py`. | Regressions in infra adapters less likely caught. | Add targeted unit/integration tests. | M | Open |

---

## Appointment Voice SaaS Product Gaps

These are product-specific gaps for the Appointment Voice SaaS fork. They do
not replace the foundation debt above. Do not mark any item Done unless product
code and tests exist.

### Product Critical

| ID | Issue | Impact | Recommendation | Roadmap mapping | Effort | Status |
|----|-------|--------|----------------|-----------------|--------|--------|
| AVS-TD-001 | No core product domain models. | The system cannot represent businesses/salons, staff, services, hours, customers, bookings, voice sessions, notifications, or calendar events. | Implement EPIC B models, migrations, schemas, services, and tenant isolation tests. | AVS-B001 to AVS-B009 | L | Open |
| AVS-TD-002 | No booking engine. | The product cannot create, list, cancel, or audit appointments. | Implement booking service/API and lifecycle rules. | AVS-D001, AVS-D003 to AVS-D006 | L | Open |
| AVS-TD-003 | No double-booking protection for appointments. | Concurrent callers/admins could book the same staff and slot once booking exists. | Enforce conflict protection with DB transactions/constraints and concurrency tests. | AVS-D002, AVS-D007 | L | Open |
| AVS-TD-004 | No IVR runtime or simulation. | The core phone-first product flow cannot be developed or demonstrated locally. | Build provider-neutral IVR session model and local simulation before real Twilio. | AVS-G001 to AVS-G010 | L | Open |
| AVS-TD-005 | No notification/calendar side-effect pipeline. | Confirmations and calendar sync cannot be reliably queued, retried, or audited. | Implement outbox-backed fake SMS and fake calendar adapters using worker patterns. | AVS-E001 to AVS-E008, AVS-F001 to AVS-F007 | XL | Open |

### Product High

| ID | Issue | Impact | Recommendation | Roadmap mapping | Effort | Status |
|----|-------|--------|----------------|-----------------|--------|--------|
| AVS-TD-006 | No reminder SMS. | Pilot customers may forget appointments; business value is weaker. | Add scheduled reminder intents and worker delivery. | P1-001 | M | Open |
| AVS-TD-007 | No customer or business reschedule flow. | Schedule changes require manual work outside the product. | Add IVR and admin reschedule workflows with SMS/calendar updates. | P1-003, P1-004 | L | Open |
| AVS-TD-008 | No IVR fallback handling. | Timeouts, invalid input, repeat requests, or backend outages can create poor caller experience. | Add timeout, invalid-input, repeat, and backend-unavailable fallback paths. | P1-005 to P1-008 | M | Open |
| AVS-TD-009 | No provider-specific webhook verification for product flows. | Real voice/SMS provider callbacks could be spoofed or replayed. | Add Twilio signature validation, webhook idempotency, and rate limiting before pilot. | AVS-H002, AVS-H005, AVS-H006 | M | Open |
| AVS-TD-010 | No product smoke tests. | The full simulated booking flow cannot be verified before pilot. | Add deterministic manual, IVR, and cancellation smoke tests. | AVS-J002 to AVS-J004 | M | Open |

### Product Medium

| ID | Issue | Impact | Recommendation | Roadmap mapping | Effort | Status |
|----|-------|--------|----------------|-----------------|--------|--------|
| AVS-TD-011 | No CRM/client profile model. | Returning-customer history and personalization are limited. | Add basic CRM clients and link bookings to clients. | P2-001, P2-002 | M | Open |
| AVS-TD-012 | No returning-customer recognition. | Repeat callers must go through the same full flow every time. | Match caller by phone and use booking history safely. | P2-003, P2-004 | M | Open |
| AVS-TD-013 | No preferred staff flow. | Customers cannot choose or reuse preferred staff. | Add preferred staff selection and last-staff suggestion. | P2-006, P2-007 | M | Open |
| AVS-TD-014 | No multi-service appointments. | Longer or combined services cannot be booked as one appointment. | Add multi-service booking model and combined-duration availability. | P2-008, P2-009 | L | Open |
| AVS-TD-015 | No waitlist. | Fully booked businesses cannot recover demand after cancellations. | Add waitlist model, offer flow, and timeout/escalation. | P2-010 to P2-012 | L | Open |
| AVS-TD-016 | No owner dashboard metrics API. | Businesses cannot measure missed-call conversion or booking volume. | Add tenant-safe metrics API. | P2-013 | M | Open |
| AVS-TD-017 | No salon hours versus staff hours model. | Availability cannot distinguish business closures from staff schedules. | Add salon hours/closures and intersect with staff hours. | P3-001 to P3-003 | M | Open |
| AVS-TD-018 | No staff time blocks or recurring blocks. | Breaks, PTO, and recurring unavailable periods are hard to represent. | Add one-off and recurring staff blocks. | P3-004, P3-005 | M | Open |

### Product Low/Future

| ID | Issue | Impact | Recommendation | Roadmap mapping | Effort | Status |
|----|-------|--------|----------------|-----------------|--------|--------|
| AVS-TD-019 | No deposits/prepayments architecture. | Businesses cannot reduce no-shows with deposits. | Write payment ADR before adding Stripe payment links or pending-payment holds. | P3-006 to P3-008 | L | Open |
| AVS-TD-020 | No multilingual IVR architecture. | Non-English callers require duplicated prompt logic later. | Add prompt-key architecture before translation content. | P3-009 | M | Open |
| AVS-TD-021 | No private staff calendar visibility policy. | Calendar integration could leak staff private event details. | Define busy/free-only rules and privacy tests. | P3-010 | M | Open |
| AVS-TD-022 | No billing/subscriptions. | The SaaS cannot enforce paid plans or limits. | Add Stripe Billing model, webhooks, plans, and limit enforcement after product MVP. | P4-007 to P4-010 | L | Open |
| AVS-TD-023 | No advanced SaaS onboarding. | Salon setup, phone provisioning, and compatibility management remain manual. | Add onboarding APIs, phone provisioning workflow, and compatibility checklist. | P4-004 to P4-006, P4-011 | L | Open |

---

## Foundation Summary

| Severity | Open | Done |
|----------|------|------|
| Critical | 0 | 4 |
| High | 0 | 11 |
| Medium | 1 | 32 |
| Low | 8 | 0 |
| **Total** | **9** | **47** |

Open counts reflect post-P2 state (374 tests, June 2026). These items are
**non-blocking** for using the repository as a frozen template; see
`TEMPLATE_FREEZE_CHECKLIST.md`.

Appointment Voice SaaS product gaps are tracked separately above and are all
Open until product runtime code and tests are implemented.
