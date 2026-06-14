# Inherited Foundation Roadmap

This is historical inherited foundation roadmap, not the active Appointment
Voice SaaS product roadmap. Active high-level product roadmap lives in
`../../ROADMAP.md`; detailed executable backlog lives in
`../appointment-saas-roadmap.md`.
Links in the preserved body below refer to the original foundation-era root
filenames; use this `docs/foundation/` directory for the archived foundation
versions.

---

# Roadmap

Prioritized engineering work for **FastAPI Production Foundation**
(`fastapi-production-foundation`).
Full issue register: `TECH_DEBT.md`. Verified capabilities: `PROJECT_STATUS.md`.

**Status key:** Not started | In progress | Done  
**Effort key:** S (<1 day) · M (1–3 days) · L (1–2 weeks) · XL (>2 weeks)  
**Risk key:** Low · Medium · High (regression or behavioral change risk)  
**ROI key:** Low · Medium · High · Very High (reduction of outage/security/maintenance pain per effort)

Only mark **Done** when verified in code and tests.

---

## Priority definitions

| Tier | Meaning |
|------|---------|
| **P0** | Must be fixed before recommending this template for production use |
| **P1** | Should be fixed soon after first production adoption |
| **P2** | Valuable improvements for scale, maintainability, and fork ergonomics |
| **P3** | Enterprise-scale or optional improvements |

---

## Summary

| Tier | Tasks | Est. effort | Primary focus | Status (June 2026) |
|------|-------|-------------|---------------|---------------------|
| P0 | 10 | ~2–3 weeks | Security defaults, production deploy safety, auth path viability | **Complete (10/10 Done)** |
| P1 | 12 | ~3–4 weeks | Session hardening, data lifecycle, CI/ops credibility | **Complete (12/12 Done)** |
| P2 | 14 | ~6–10 weeks | Scale, maintainability, and fork ergonomics | **Complete (14/14 Done)** |
| P3 | 8 | ~4–6 weeks | Enterprise observability, test depth, optional hardening | Not started |

**Recommended sequence:** P0, P1, and P2 complete → P3 for enterprise forks as needed.

---

## P0 — Must fix before production recommendation

**Status:** All tasks complete and merged (June 2026). P0 production-readiness
blockers are closed; the template may be recommended for production-oriented
forks when operators follow deployment docs. This is not a claim of
enterprise-grade or fully finished platform status.

| # | Task | Debt IDs | Effort | Risk | ROI | Status |
|---|------|----------|--------|------|-----|--------|
| 1 | **Legacy route production gate** — `LEGACY_ROUTES_ENABLED` env (default off in production); tests + deprecation doc update | TD-002 | S | Low | Very High | Done |
| 2 | **Worker processing-queue recovery** — reaper or visibility timeout for `app_jobs_processing` | TD-003 | M | Medium | Very High | Done |
| 3 | **Production runtime scaling baseline** — multi-worker/gunicorn guidance, pool sizing formula, startup log of effective DB pool | TD-001, TD-013 | M | Low | Very High | Done |
| 4 | **Proxy-aware rate limiting** — trusted forwarded client IP; required for any reverse-proxy deployment | TD-006 | M | Medium | Very High | Done |
| 5 | **Metrics endpoint hardening** — bearer auth for `/metrics` in production (`METRICS_REQUIRE_AUTH`, `METRICS_BEARER_TOKEN`) and deployment guidance; network-level bind/restriction remains an operator responsibility | TD-005 | S | Low | High | Done |
| 6 | **JWT algorithm single source of truth** — unify encode/decode on `settings.algorithm` | TD-007 | S | Low | High | Done |
| 7 | **RBAC role input validation** — reject arbitrary `role` strings on admin update | TD-008 | S | Low | High | Done |
| 8 | **Upload production guard** — fail startup in production when file features are used without a real malware scanner URL | TD-009 | S | Low | High | Done |
| 9 | **Worker poison-message handling** — unknown job types → DLQ, never silent ack | TD-011 | S | Low | High | Done |
| 10 | **Redis production contract** — document Redis as a hard dependency, HA requirements, and explicit fail-closed behavior for refresh rotation | TD-004 | M | Medium | High | Done |

**P0 exit criteria:** Met as of June 2026 — reverse-proxy rate limits work,
legacy routes are gated in production, worker jobs are not silently lost,
production config rejects unsafe upload defaults, and metrics require auth by
default in production.

**P0 cumulative estimate:** ~2–3 engineer-weeks · **Risk:** Medium overall · **ROI:** Very High

---

## P1 — Fix soon after production adoption

**Status:** All tasks complete and merged (June 2026).

| # | Task | Debt IDs | Effort | Risk | ROI | Status |
|---|------|----------|--------|------|-----|--------|
| 11 | **Refresh/session hardening** — embed `token_version` in refresh tokens; rate limits on `/auth/refresh` and `/auth/logout`; env-driven JWT TTLs | TD-014, TD-015, TD-046 | M | Medium | High | Done |
| 12 | **Graceful shutdown** — SIGTERM drain for API and worker; reduce in-flight job loss on deploy | TD-017 | M | Medium | High | Done |
| 13 | **Idempotency retention job** — purge expired `idempotency_records` rows in worker maintenance | TD-010 | S | Low | High | Done |
| 14 | **Redis resilience implementation** — circuit breaker or bounded retry for non-auth-critical cache paths; clearer error responses when Redis is down | TD-004 | L | High | High | Done |
| 15 | **Container health and readiness** — Docker `HEALTHCHECK`; optional S3 head-bucket when uploads enabled | TD-016, TD-032 | S | Low | High | Done |
| 16 | **CI and deploy reliability** — gate `docker-build` on tests; fail silent backup cron; dedupe migration steps; clarify `latest` tag policy | TD-035, TD-036, TD-043, TD-044 | S | Low | High | Done |
| 17 | **Observability asset and doc repair** — add `.env.observability.example`, Grafana Prometheus datasource, dashboard stub or fix README; fix Promtail target; document Alertmanager stub | TD-037, TD-038, TD-048 | M | Low | High | Done |
| 18 | **Webhook ingress baseline** — max body size; per-IP/provider rate limits | TD-019 | S | Low | Medium | Done |
| 19 | **Global error handler** — generic 500 handler; enforce non-debug production guidance | TD-020 | S | Low | Medium | Done |
| 20 | **Tenant ContextVar reset** — clear tenant context at request entry in middleware | TD-034 | S | Low | Medium | Done |
| 21 | **Password-reset idempotency race** — DB-level dedup keyed by `job_id` across commit/marker window | TD-022 | M | Medium | Medium | Done |
| 22 | **Webhook event retention** — scheduled purge/archival for `webhook_events` | TD-024 | S | Low | Medium | Done |

**P1 exit criteria:** Met as of June 2026 — rolling deploys drain safely, session
revocation is hardened, CI blocks broken images, observability docs match the
repo, and TTL-backed tables have retention jobs.

**P1 cumulative estimate:** ~3–4 engineer-weeks · **Risk:** Medium · **ROI:** High

---

## P2 — Valuable improvements

**Status:** All tasks complete and merged (June 2026).

| # | Task | Debt IDs | Effort | Risk | ROI | Status |
|---|------|----------|--------|------|-----|--------|
| 23 | **Sync scaling path (short term)** — official multi-worker benchmark doc and load-test profiles for bcrypt/login path | TD-012 | M | Low | High | Done |
| 24 | **Async architecture spike (long term)** — evaluate async SQLAlchemy + async routes; decision record for forks | TD-012 | XL | High | Medium | Done |
| 25 | **Worker observability** — scrape worker metrics in prod topology; tune maintenance/promote loop | TD-023, TD-042 | M | Medium | High | Done |
| 26 | **Pagination and admin search at scale** — keyset pagination; pg_trgm or prefix-only email search | TD-026, TD-027 | M | Medium | High | Done |
| 27 | **Cache invalidation redesign** — versioned keys instead of Redis `SCAN` pattern delete | TD-028 | M | Medium | Medium | Done |
| 28 | **Storage performance** — cached boto3 client; streaming multipart upload; async scan worker for presigned completes | TD-029, TD-030, TD-031 | M | Medium | High | Done |
| 29 | **Audit log lifecycle** — retention, partitioning, or export job | TD-025 | M | Medium | Medium | Done |
| 30 | **Transaction integrity** — single transaction for user update + audit log (or outbox) | TD-033 | M | Medium | Medium | Done |
| 31 | **Request pipeline hygiene** — pure ASGI logging middleware; replace `BaseHTTPMiddleware` | TD-045 | M | Medium | Medium | Done |
| 32 | **Python runtime baseline** — evaluate 3.12/3.13 LTS as default Docker base | TD-018 | S | Medium | Medium | Done |
| 33 | **Schema consolidation** — merge duplicate `UserRead` definitions | TD-047 | S | Low | Medium | Done |
| 34 | **Tenant seed refactor** — move default tenant out of migration bulk insert | TD-039 | M | High | Medium | Done |
| 35 | **Platform admin model clarity** — document demo-only boundary or separate operator table design | TD-040 | L | High | Medium | Done |
| 36 | **Service layer decoupling** — domain exceptions instead of `HTTPException` in services | TD-041 | L | High | Medium | Done |

**P2 exit criteria:** Template handles 100k-user admin workloads without pagination/table-bloat cliffs; file and worker paths are observable and efficient; forks inherit clearer extension patterns.

**P2 cumulative estimate:** ~6–10 engineer-weeks · **Risk:** Medium–High · **ROI:** Medium–High

---

## P3 — Enterprise-scale or optional

Optional post-freeze improvements for forks that need deeper enterprise gates.
The template foundation (P0–P2) is complete and cloneable without P3.

| # | Task | Debt IDs | Effort | Risk | ROI | Status |
|---|------|----------|--------|------|-----|--------|
| 37 | **PostgreSQL RLS example** — optional migration + security guide for defense-in-depth tenancy | TD-021 | L | High | Medium | Not started |
| 38 | **OpenTelemetry integration** — optional OTel middleware hook and fork documentation | TD-050 | L | Medium | Medium | Not started |
| 39 | **Adversarial security test suite** — JWT tampering, upload path traversal, metrics exposure regression tests | TD-051 | M | Low | High | Not started |
| 40 | **E2E worker integration test** — Compose test: enqueue → worker → email stub | TD-052 | M | Medium | High | Not started |
| 41 | **Deploy script test coverage** — dry-run tests for smoke/deploy shell scripts | TD-053 | S | Low | Medium | Not started |
| 42 | **Observability CI validation** — Prometheus rule lint; observability compose smoke job | TD-054 | M | Low | Medium | Not started |
| 43 | **Extended migration testing** — multi-revision downgrade rehearsal | TD-055 | M | Medium | Medium | Not started |
| 44 | **Adapter test coverage** — raise coverage for email, storage, and db session modules | TD-056 | M | Low | Medium | Not started |
| 45 | **CSP header** — add when serving HTML error responses | TD-049 | S | Low | Low | Not started |

**P3 exit criteria:** Enterprise forks get tracing hooks, stronger security regression gates, and broader integration coverage without product-specific SaaS features.

**P3 cumulative estimate:** ~4–6 engineer-weeks · **Risk:** Low–Medium · **ROI:** Medium (High for security test suite and E2E worker test)

---

## Debt ID coverage

Every open item in `TECH_DEBT.md` maps to exactly one roadmap task above.

| Debt ID | Roadmap task |
|---------|--------------|
| TD-001, TD-013 | P0 #3 |
| TD-002 | P0 #1 |
| TD-003 | P0 #2 |
| TD-004 | P0 #10 (contract) · P1 #14 (implementation) |
| TD-005 | P0 #5 |
| TD-006 | P0 #4 |
| TD-007 | P0 #6 |
| TD-008 | P0 #7 |
| TD-009 | P0 #8 |
| TD-010 | P1 #13 |
| TD-011 | P0 #9 |
| TD-012 | P2 #23 (benchmark) · P2 #24 (async spike) |
| TD-014, TD-015, TD-046 | P1 #11 |
| TD-016, TD-032 | P1 #15 |
| TD-017 | P1 #12 |
| TD-018 | P2 #32 |
| TD-019 | P1 #18 |
| TD-020 | P1 #19 |
| TD-021 | P3 #37 |
| TD-022 | P1 #21 |
| TD-023, TD-042 | P2 #25 |
| TD-024 | P1 #22 |
| TD-025 | P2 #29 |
| TD-026, TD-027 | P2 #26 |
| TD-028 | P2 #27 |
| TD-029, TD-030, TD-031 | P2 #28 |
| TD-033 | P2 #30 |
| TD-034 | P1 #20 |
| TD-035, TD-036, TD-043, TD-044 | P1 #16 |
| TD-037, TD-038, TD-048 | P1 #17 |
| TD-039 | P2 #34 |
| TD-040 | P2 #35 |
| TD-041 | P2 #36 |
| TD-045 | P2 #31 |
| TD-047 | P2 #33 |
| TD-049 | P3 #45 |
| TD-050 | P3 #38 |
| TD-051 | P3 #39 |
| TD-052 | P3 #40 |
| TD-053 | P3 #41 |
| TD-054 | P3 #42 |
| TD-055 | P3 #43 |
| TD-056 | P3 #44 |

---

## Reprioritization notes (vs. prior roadmap)

| Change | Rationale |
|--------|-----------|
| Proxy-aware rate limits **P1 → P0** | Every production deploy uses a reverse proxy; current limits are broken or harmful without this |
| RBAC role validation **P1 → P0** | Small change; prevents immediate admin lockout/privilege bugs in forks |
| JWT algorithm fix **P1 → P0** | Config footgun that breaks auth silently |
| Upload production guard **P1 → P0** | Template ships file uploads; unsafe prod default is a security incident waiting to happen |
| Worker DLQ **P1 → P0** | Silent job loss is unacceptable for a production-recommended worker queue |
| Redis full circuit breaker **P0 → P1** | Operator HA is required first; implementation is larger and higher regression risk |
| Redis production contract **new P0** | Documents hard dependency and fail-closed auth behavior without large code change |
| Observability doc fix stays **P1** | Hurts template credibility but not a production outage on day one |
| Async architecture **split P2** | Benchmark/multi-worker doc delivers ROI now; full async rewrite is XL with high risk |
| HEALTHCHECK **P1** | Standard ops hygiene, not a day-one blocker if manual health checks exist |
| Adversarial tests **P3** | High ROI but optional until P0/P1 controls are in place |

---

## Downstream project decisions (not template code)

These remain the responsibility of each fork:

- Production hosting platform (K8s, PaaS, VM Compose)
- Secret manager and rotation runbooks
- Backup provider, PITR policy, and restore targets
- Concrete malware scanner service
- Client migration off deprecated unversioned routes
- OAuth/SAML/MFA and invite-only registration flows
- Product-specific webhook processing pipelines

---

## Completed remediation (historical)

June 2026 audit remediation (verified in code):

| PR | Item |
|----|------|
| #29 | Docs/status sync + `docs/template-onboarding.md` |
| #30 | Auth login/register rate limits |
| #31 | Worker password-reset idempotency |
| #32 | Staging config validators |
| #33 | Platform vs tenant admin roles |
| #34 | Registration policy gate |
| #35 | Access token `token_version` invalidation |
| #36 | Production runtime examples + deploy checklist |
| #37 | Scheduled backup workflow + PITR checklist |
| #38 | Pull-request load threshold CI smoke |
| #39 | Malware scanning boundary docs/tests |
| #40 | Legacy route deprecation policy |
| #41 | `make validate` coverage floor parity |
| #44 | AI rules refactor + CI/pre-commit policy guards |
| #45 | P0 #1 Legacy route production gate (TD-002) |
| #46 | P0 #2 Worker processing-queue reaper (TD-003) |
| #47 | P0 #3 Production runtime scaling baseline (TD-001, TD-013) |
| #48 | P0 #4 Proxy-aware rate limiting (TD-006) |
| #49 | P0 #5 Metrics endpoint hardening (TD-005) |
| #50 | P0 #6 JWT algorithm single source (TD-007) |
| #51 | P0 #7 RBAC role input validation (TD-008) |
| #52 | P0 #8 Upload production guard (TD-009) |
| #53 | P0 #9 Worker unknown job types → DLQ (TD-011) |
| #54 | P0 #10 Redis production contract doc (TD-004 contract) |
| #56 | P1 #11 Refresh/session hardening (TD-014, TD-015, TD-046) |
| #57 | P1 #12 Graceful shutdown (TD-017) |
| #58 | P1 #13 Idempotency retention (TD-010) |
| #59 | P1 #20 Tenant ContextVar reset (TD-034) |
| #60 | P1 #19 Global error handler (TD-020) |
| #61 | P1 #22 Webhook event retention (TD-024) |
| #62 | P1 #18 Webhook ingress baseline (TD-019) |
| #63 | P1 #15 Container health/readiness (TD-016, TD-032) |
| #64 | P1 #16 CI/deploy reliability (TD-035, TD-036, TD-043, TD-044) |
| #65 | P1 #17 Observability asset/doc repair (TD-037, TD-038, TD-048) |
| #66 | P1 #21 Password-reset idempotency (TD-022) |
| #67 | P1 #14 Redis resilience implementation (TD-004) |
| #69 | P2 #33 Consolidate `UserRead` schema (TD-047) |
| #70 | P2 #30 User update + audit log single transaction (TD-033) |
| #71 | P2 #29 Audit log retention job (TD-025) |
| #72 | P2 #27 Versioned user-list cache keys (TD-028) |
| #73 | P2 #31 Pure ASGI request middleware (TD-045) |
| #74 | P2 #23 Sync scaling benchmark doc (TD-012) |
| #75 | P2 #24 Async architecture ADR (TD-012) |
| #76 | P2 #35 Platform admin model docs (TD-040) |
| #77 | P2 #32 Python 3.13 runtime baseline (TD-018) |
| #78 | P2 #25 Worker observability (TD-023, TD-042) |
| #79 | P2 #26 Keyset pagination and admin email search (TD-026, TD-027) |
| #80 | P2 #28 Storage performance (TD-029, TD-030, TD-031) |
| #81 | P2 #34 Tenant seed refactor (TD-039) |
| #82 | P2 #36 Domain exceptions in service layer (TD-041) |

---

## How to use this file

1. **P0, P1, and P2 are complete** — proceed with **P3** tasks as needed.
2. Create a feature branch per task, run `make validate`, merge via PR.
3. Mark debt items **Done** in `TECH_DEBT.md` only after code verification.
4. Move verified capabilities to `PROJECT_STATUS.md`.
5. Update task **Status** here when merged.
