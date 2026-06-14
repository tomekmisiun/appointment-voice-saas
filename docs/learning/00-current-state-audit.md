# Current State Audit (code-verified)

**As of:** 2026-06-14 · **Method:** routes, models, migrations, tests, roadmap —
not README alone.

Use this file to defend what the repo **actually** contains today.

## Executive summary

| Layer | Status |
|-------|--------|
| FastAPI foundation (auth, tenants, users, files, webhooks, worker, CI) | **Implemented** |
| Appointment domain (business → booking) | **Implemented** (EPIC B–D core) |
| Availability engine | **Implemented** (EPIC C) |
| Notifications / SMS outbox | **Planned** (EPIC E) |
| Calendar adapter | **Planned** (EPIC F) |
| IVR / voice | **Planned** (EPIC G+) |
| Frontend / billing | **Planned** |

The product is a **working backend slice** (configure salon + availability +
bookings + audit), not the full voice/SMS/calendar MVP described in
`docs/demo-flow.md`.

---

## Status legend

| Label | Meaning |
|-------|---------|
| **Implemented** | Code + migration + tests (or CI) verify behavior |
| **Partially implemented** | Some layers exist; gaps documented |
| **Planned** | Docs/roadmap only |
| **Stale** | Doc contradicts code |
| **Unclear** | Needs human decision or more audit |

---

## 1. Inherited FastAPI foundation

| Area | Status | Evidence |
|------|--------|----------|
| App bootstrap, middleware, errors | Implemented | `app/main.py`, `app/core/middleware.py`, `tests/test_middleware.py` |
| `/api/v1` versioning + legacy routes | Implemented | `app/api/v1.py`, `tests/test_api_versioning.py` |
| JWT auth, refresh, RBAC | Implemented | `app/api/routes/auth.py`, `tests/test_auth.py` |
| Users CRUD + audit on mutations | Implemented | `app/api/routes/users.py`, `tests/test_users.py` |
| Multi-tenancy (Tenant, tenant_id on users) | Implemented | `app/models/tenant.py`, `tests/test_tenancy.py` |
| Admin + audit log listing | Implemented | `app/api/routes/admin.py`, `tests/test_audit_logs.py` |
| File uploads (S3/MinIO, scan hook) | Implemented | `app/api/routes/files.py`, `tests/test_files.py` |
| Webhooks + idempotency | Implemented | `app/api/routes/webhooks.py`, `tests/test_webhooks.py` |
| Redis rate limit, cache, job queue | Implemented | `app/core/redis.py`, `tests/test_rate_limit.py`, `tests/test_job_queue.py` |
| Background worker | Implemented | `app/worker.py`, `tests/test_worker.py` |
| Health + Prometheus metrics | Implemented | `app/api/routes/health.py`, `tests/test_health.py` |
| Docker Compose dev stack | Implemented | `docker-compose.yml`, `Makefile` |
| CI (ruff, pytest 85% cov, policy guards) | Implemented | `.github/workflows/ci.yml` |
| Password reset email jobs | Implemented | `app/services/password_reset_service.py` |

Foundation detail archive: `docs/foundation/template-project-status.md`.

---

## 2. Appointment Voice SaaS runtime (product)

### Core domain (EPIC B)

| Entity | Model | Service | API | Tests | Status |
|--------|-------|---------|-----|-------|--------|
| Business | `app/models/business.py` | `business_service.py` | `GET/POST/PATCH /api/v1/businesses` | `test_businesses.py` | **Implemented** |
| Staff | `staff.py` | `staff_service.py` | nested under business | `test_staff.py` | **Implemented** |
| Service (appointment type) | `service.py` | `service_service.py` | nested | `test_services.py` | **Implemented** |
| WorkingHours | `working_hours.py` | `working_hours_service.py` | nested | — | **Partially** (no dedicated route test file) |
| AvailabilityException | `availability_exception.py` | `availability_exception_service.py` | nested | — | **Partially** (no dedicated route test file) |
| Customer | `customer.py` | `customer_service.py` | **none** (used via booking) | via booking tests | **Partially** |
| Booking | `booking.py` | `booking_service.py` | nested bookings CRUD + cancel | `test_bookings.py` | **Implemented** |

Migrations: `1a2b3c4d5e6f_add_appointment_domain_tables.py`, `2b3c4d5e6f7a_add_booking_no_overlap_constraint.py`, `32e2a5c45a2d_add_booking_audit_log.py`.

### Availability (EPIC C)

| Capability | Status | Evidence |
|------------|--------|----------|
| Slot generation from hours + duration | Implemented | `availability_service.py`, `test_availability.py` |
| Exclude confirmed bookings | Implemented | same |
| Exceptions (closures / special hours) | Implemented | same |
| Timezone / DST | Implemented | same |
| `GET .../availability` | Implemented | `app/api/routes/availability.py` |

### Booking engine (EPIC D)

| Capability | Status | Evidence |
|------------|--------|----------|
| Create / list / read / cancel | Implemented | `booking_service.py`, `test_bookings.py` |
| DB double-booking (`EXCLUDE gist`) | Implemented | migration `2b3c4d5e6f7a`, `test_concurrency.py` |
| Audit on create/cancel + actor/source | Implemented | `test_booking_audit.py` |

### Not implemented (product runtime)

| Area | Status | Roadmap |
|------|--------|---------|
| Notification outbox / SMS | Planned | AVS-E001+ |
| Calendar adapter | Planned | AVS-F001+ |
| IVR / VoiceSession | Planned | AVS-G001+ |
| Call transfer | Planned | AVS-I001+ |
| E2E smoke scripts | Planned | AVS-J001+ |
| Customer HTTP API | Planned / unclear | not in roadmap explicitly |
| Frontend | Planned | — |

---

## 3. Planned documentation only

| Doc | Role |
|-----|------|
| `docs/demo-flow.md` | Target end-to-end call flow — **not runnable yet** |
| `docs/product-scope.md` | Product vision |
| `docs/domain-model.md` | Vocabulary (may ahead of code) |
| `docs/appointment-saas-roadmap.md` | Backlog — check `[x]` vs code |
| `docs/adr/0002-*.md` | Architecture decisions (partially built) |

---

## 4. Remaining doc inconsistencies

| Location | Issue |
|----------|-------|
| `docs/domain-model.md` | May describe planned entities not yet in migrations — cross-check before citing |

**Fixed:** OpenAPI title uses `settings.app_name` (default `"Appointment Voice SaaS API"` in `app/core/config.py`).

**Source of truth order:** code → tests → migrations → `PROJECT_STATUS.md`
(verified section) → `docs/learning/00-current-state-audit.md` → roadmap → README.

**Refresh rule:** update this file in the same change set when closing roadmap
items or changing verified product scope (see `docs/learning/README.md`).

---

## 5. Test coverage map (product)

| Area | Primary tests |
|------|----------------|
| Tenant isolation (product tables) | `tests/test_product_tenant_isolation.py` |
| Businesses, staff, services | `test_businesses.py`, `test_staff.py`, `test_services.py` |
| Bookings + concurrency | `test_bookings.py`, `test_concurrency.py`, `test_booking_audit.py` |
| Availability | `test_availability.py` |
| Foundation tenancy | `test_tenant_isolation.py`, `test_tenancy.py` |

---

## 6. Next milestone (roadmap-aligned)

**EPIC E — AVS-E001:** notification outbox model (see `docs/appointment-saas-roadmap.md`).
