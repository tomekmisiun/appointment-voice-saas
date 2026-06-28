# Technical Debt — VoxSlot

This is the active product gap register. Historical completed work and prior
audit tables are archived under [`docs/archive/`](docs/archive/).

Status legend: `Open`, `In Progress`, `Accepted`, `Mitigated`.

## Critical

| ID | Problem | Evidence | Impact | Priority | Suggested resolution | Validation |
|---|---|---|---|---|---|---|
| OPS-001 | Production API health is not guaranteed from repository evidence. | Historical audits recorded a Railway 502; current live status was not checked during this docs-only audit. | Public demo and pilot traffic may fail even when local dev works. | Critical | Inspect Railway logs/status, repair startup/config, and add post-deploy smoke. | CI/deploy smoke hits `/health/live` and `/health/ready` after deploy. |

## High

| ID | Problem | Evidence | Impact | Priority | Suggested resolution | Validation |
|---|---|---|---|---|---|---|
| SEC-001 | Per-business RBAC is not wired into runtime authorization. | `BusinessMembership` model/tests exist; auth checks use `User.role` and frontend mirrors that hierarchy. | A tenant admin model cannot safely express business-specific owner/staff permissions. | High | Complete SAC-005 authorization context and route checks. | Cross-business role tests prove allowed/denied access per membership. |
| UX-001 | Owner dashboard lacks key configuration screens. | Frontend routes cover dashboard/bookings/staff; services, hours, recurring blocks, exceptions, clients, calendar setup, metrics, and telephony screens are missing. | Owners must use API/operator tools for core setup. | High | Build screens against existing backend APIs and add missing aggregation endpoints only where needed. | Frontend tests and API/BFF tests cover each new screen. |
| UX-002 | Customers have no public booking management link. | No public HMAC cancel/reschedule endpoint or SMS link workflow exists. | Customers must call again or contact the business to change bookings. | High | Add signed public booking-management link and route. | Token tamper/expiry tests, cancel/reschedule tests, SMS content tests. |
| TEST-001 | No post-deploy production smoke gate. | `ci.yml` deploys to Railway after CI; no live `/health` smoke is enforced after deployment. Manual `deploy.yml` has optional smoke. | A successful deployment can still leave production unavailable. | High | Add post-deploy API/frontend smoke with safe credentials or health-only checks. | Failed health check fails the deploy job. |

## Medium

| ID | Problem | Evidence | Impact | Priority | Suggested resolution | Validation |
|---|---|---|---|---|---|---|
| ARCH-002 | Telephony inventory is incomplete on `main`. | `BusinessPhoneNumber` and `telephony_status` are absent; Twilio routing uses `Business.phone`. | Operators cannot manage multiple numbers or phone assignment state cleanly. | Medium | Add phone-number model/operator API/status card if product direction requires it. | Migration/model tests, routing tests, admin/API tests. |
| ARCH-003 | SMS messages are hardcoded English strings. | Notification service/provider paths use hardcoded message text; no `SmsTemplate` model. | Non-English businesses and per-business copy are unsupported. | Medium | Add locale field/template policy before user-editable templates. | Locale rendering tests and injection/placeholder validation tests. |
| ARCH-005 | Calendar production integration is partial. | Calendar models and fake provider exist; no OAuth flow or frontend setup. | Calendar sync is not usable by owners without future integration work. | Medium | Implement provider connection flow or keep documented as future scope. | OAuth/setup tests or explicit decision to keep fake-only. |
| TEST-002 | No browser-driven E2E suite. | Frontend uses Vitest/component tests only. | Cross-layer login/dashboard/demo workflows can regress. | Medium | Add Playwright/Cypress only when workflows justify the maintenance cost. | E2E covers login, dashboard bookings, and demo read-only behavior. |
| SEC-003 | Staff invitation schema may diverge between production and fresh databases. | Repository has a no-op SAC-009 migration stub and historical recovery notes. | Future staff invitation implementation could conflict with production schema. | Medium | Verify production Alembic state before implementing SAC-009; use guarded migration. | `alembic current` evidence and idempotent migration tests. |
| OBS-001 | Booking/IVR failure metrics are incomplete. | Metrics cover HTTP, dependency checks, worker jobs, provider failures, and failed queue depth; no dedicated booking/IVR failure counters. | Operators have less direct signal for product-specific failures. | Medium | Add product-specific counters/alerts around booking and IVR failure paths. | Metrics tests and Prometheus alert rule checks. |

## Low

| ID | Problem | Evidence | Impact | Priority | Suggested resolution | Validation |
|---|---|---|---|---|---|---|
| SEC-004 | Tenant-isolation enforcement is not systematic in CI. | Route/service tests exist, but no general guard prevents new unscoped queries. | Future endpoints may miss tenant/business filters. | Low | Add focused guard patterns or review checklist automation without overfitting. | New guard fails on representative unsafe route/query fixture. |
| OPS-002 | Node version is documented in `package.json` but not pinned in a root version file. | `frontend/package.json` has `engines.node=^22.13.0`; no `.nvmrc` or `.node-version`. | Local frontend builds may use a different Node version. | Low | Add a version file if team workflow needs it. | Local setup docs and CI use the same Node version. |
| UX-004 | IVR simulator has no frontend UI. | Backend simulator endpoints exist; no frontend simulator route. | Demoing IVR requires API tools. | Low | Add a simple internal simulator UI if it helps demos. | Frontend tests cover simulator state transitions. |

## Accepted Or Deferred

| ID | Decision | Reason |
|---|---|---|
| BILLING-001 | Stripe payment links and subscriptions are deferred. | Not required for the local demo or immediate pilot validation. |
| CAL-ADR | Two-way calendar sync remains future-scope. | ADRs 0005 and 0006 intentionally constrain current calendar behavior. |

## Update Rules

- Keep this file focused on active, actionable gaps.
- Do not add completed implementation history here.
- Mark a gap resolved only when code/configuration and tests or CI evidence
  prove it.
- Put future delivery sequencing in [`ROADMAP.md`](ROADMAP.md).
