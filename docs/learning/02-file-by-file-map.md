# File-by-File Map (important files)

Not every file — focus on files you touch or must explain in interviews.

## Entry and wiring

| File | What it does | Called by |
|------|--------------|-----------|
| `app/main.py` | FastAPI app, middleware, routers | Uvicorn (`docker compose` / prod) |
| `app/api/v1.py` | Registers all `/api/v1` routers | `main.py` |
| `app/core/config.py` | Settings from env; prod validators | Everywhere via `settings` |
| `app/db/session.py` | DB engine, `get_db()` dependency | Routes, worker |

## HTTP routes (foundation)

| File | Prefix / path | Auth |
|------|---------------|------|
| `routes/auth.py` | `/auth/*` | Public login/register |
| `routes/users.py` | `/api/v1/users` | Admin |
| `routes/tenants.py` | `/api/v1/admin/tenants` | Platform admin |
| `routes/admin.py` | `/api/v1/admin/*` | Admin (audit logs) |
| `routes/files.py` | `/api/v1/files` | Authenticated |
| `routes/webhooks.py` | `/api/v1/webhooks/*` | Signature verified |
| `routes/health.py` | `/health` | Public |
| `routes/metrics.py` | `/metrics` | Configurable auth |

## HTTP routes (appointment product)

All nested under `/api/v1/businesses/{business_id}/...` unless noted.

| File | Resource |
|------|----------|
| `routes/businesses.py` | Business CRUD |
| `routes/staff.py` | Staff |
| `routes/services.py` | Services (haircut, etc.) |
| `routes/working_hours.py` | Recurring hours |
| `routes/availability_exceptions.py` | Closures / special hours |
| `routes/availability.py` | **GET** available slots |
| `routes/bookings.py` | Create, list, get, cancel bookings |

## Dependencies (cross-cutting)

| File | Purpose |
|------|---------|
| `dependencies/auth.py` | `get_current_user`, `require_role`, JWT |
| `dependencies/tenant.py` | Tenant membership checks |
| `dependencies/rate_limit.py` | Redis sliding window |
| `dependencies/idempotency.py` | Safe retries for mutating APIs |

## Services — foundation

| File | Responsibility |
|------|----------------|
| `auth_service.py` | Login, tokens, refresh rotation |
| `user_service.py` | User CRUD |
| `tenant_service.py` | Tenant lifecycle |
| `audit_log_service.py` | Write/read audit rows |
| `storage_service.py` | S3 upload/download |
| `webhook_service.py` | Verify + store webhook events |
| `password_reset_service.py` | Tokens + email job enqueue |
| `idempotency_service.py` | Idempotency keys |

## Services — appointment product

| File | Responsibility |
|------|----------------|
| `business_service.py` | Business CRUD; `require_business()` tenancy guard |
| `staff_service.py` | Staff CRUD |
| `service_service.py` | Service (duration, price metadata) |
| `working_hours_service.py` | Weekly schedule rows |
| `availability_exception_service.py` | One-off schedule overrides |
| `customer_service.py` | Phone dedupe, get/create customer |
| `availability_service.py` | **Slot generation** |
| `booking_service.py` | Create/cancel booking, double-book check + audit |

Pattern: `require_*()` loads row **with tenant_id filter** → raises `NotFoundError`
if missing or wrong tenant.

## Models

| File | Table | Notes |
|------|-------|-------|
| `tenant.py`, `user.py` | Foundation | |
| `business.py` | `businesses` | timezone, phone |
| `staff.py`, `service.py` | staff, services | scoped to business |
| `working_hours.py`, `availability_exception.py` | schedules | |
| `customer.py` | customers | phone normalized per business |
| `booking.py` | bookings | status, source, staff, times |
| `audit_log.py` | audit_logs | includes booking actions |

## Core infrastructure

| File | Role |
|------|------|
| `core/security.py` | Password hash, JWT encode/decode |
| `core/domain_errors.py` | `NotFoundError`, `ConflictError` → HTTP mapping |
| `core/exception_handlers.py` | Maps errors to JSON envelope |
| `core/job_queue.py` | Redis list queues, retry, DLQ |
| `core/redis.py` | Redis client |
| `core/metrics.py` | Prometheus counters/histograms |
| `worker.py` | Dequeue jobs, maintenance (audit cleanup, etc.) |

## Migrations (product-related)

| Revision | What |
|----------|------|
| `1a2b3c4d5e6f` | All appointment domain tables |
| `2b3c4d5e6f7a` | `EXCLUDE` constraint — no overlapping staff bookings |
| `32e2a5c45a2d` | Audit `target_booking_id`, `source` |

## Tests (where behavior is proven)

| File | Protects |
|------|----------|
| `test_product_tenant_isolation.py` | Cross-tenant denial on product APIs |
| `test_businesses.py`, `test_staff.py`, `test_services.py` | CRUD |
| `test_availability.py` | Slot engine |
| `test_bookings.py`, `test_concurrency.py` | Booking + race |
| `test_booking_audit.py` | Audit trail |
| `test_auth.py`, `test_tenant_isolation.py` | Foundation security |

## AI / workflow (for agents)

| Path | Role |
|------|------|
| `.ai-rules/` | Binding rules |
| `.ai-rules/learning-mode.md` | Mentor-style completion format |
| `docs/learning/` | Human + agent learning maps |
| `scripts/ci/` | Policy guards enforced in CI |
