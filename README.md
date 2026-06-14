# Appointment Voice SaaS

Appointment Voice SaaS is a planned mini SaaS for barbers and other local
service businesses that miss calls while serving customers. The target product
answers a business phone number with IVR, lets the caller choose a service and
available slot, creates the booking in the backend, syncs it to a calendar,
sends SMS notifications, and later supports cancellation, reschedule, and call
transfer to staff.

## Current Status

See **[`PROJECT_STATUS.md`](PROJECT_STATUS.md)** (verified section) and
**[`docs/learning/00-current-state-audit.md`](docs/learning/00-current-state-audit.md)**
for code-verified state. Do not trust this README's high-level bullets alone.

- **Implemented:** foundation app + appointment domain (business, staff, service,
  hours, availability, bookings, audit) with tests and migrations.
- **Planned:** IVR, SMS outbox, calendar adapter, call transfer, smoke demos,
  billing, frontend (roadmap EPIC E–J).

## What Exists Today

Inherited foundation capabilities available for reuse:

- FastAPI application structure with versioned API routing.
- PostgreSQL, SQLAlchemy, Alembic migrations, and database session patterns.
- Redis-backed rate limiting, caching, job queue, and idempotency patterns.
- Worker patterns with retries, delayed jobs, failed-job handling, and
  maintenance jobs.
- Auth/users/tenant foundation with JWT auth, RBAC, user management, and tenant
  scoping patterns.
- Webhook verification and idempotency patterns.
- Observability, request IDs, structured logging, health checks, and Prometheus
  metrics.
- Docker Compose local stack, production Docker examples, CI, tests, and policy
  guards.
- AI workflow rules in `.ai-rules/`, with optional agents and commands.

## What Does Not Exist Yet

Appointment Voice SaaS gaps (verify in [`docs/learning/00-current-state-audit.md`](docs/learning/00-current-state-audit.md)):

- IVR runtime flow or local IVR simulation.
- SMS provider integration or product notification outbox.
- Calendar sync or product calendar adapter.
- Call transfer.
- Product-specific end-to-end smoke tests (demo scripts).
- Dedicated Customer HTTP CRUD API (customers exist via booking flow only).
- Billing, subscriptions, or frontend.

## Product Documentation Map

| Document | Purpose |
|----------|---------|
| [`docs/learning/`](docs/learning/) | Code-verified mental maps and interview defense (start here to learn the repo) |
| [`docs/product-scope.md`](docs/product-scope.md) | Product users, problem, MVP flow, non-goals, and assumptions |
| [`docs/domain-model.md`](docs/domain-model.md) | Planned Appointment Voice SaaS domain vocabulary |
| [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) | Detailed executable product backlog |
| [`PROJECT_STATUS.md`](PROJECT_STATUS.md) | Verified Appointment Voice SaaS status |
| [`ROADMAP.md`](ROADMAP.md) | High-level Appointment Voice SaaS roadmap |
| [`TECH_DEBT.md`](TECH_DEBT.md) | Active product technical debt and gaps |

## Inherited Foundation References

The foundation docs are still useful, but they are reference material for the
backend inherited from the template, not the active product roadmap/status.

| Document | Purpose |
|----------|---------|
| [`docs/foundation/`](docs/foundation/) | Archived foundation status, roadmap, debt, and freeze checklist |
| [`docs/template-onboarding.md`](docs/template-onboarding.md) | Historical clone/fork onboarding guide for the foundation |
| [`docs/template-usage.md`](docs/template-usage.md) | Historical quick reference for using the foundation |
| [`docs/commands.md`](docs/commands.md) | Makefile command reference |
| [`docs/production-deployment.md`](docs/production-deployment.md) | Deployment model inherited from the foundation |
| [`docs/worker-reliability.md`](docs/worker-reliability.md) | Worker reliability patterns |
| [`docs/webhook-idempotency.md`](docs/webhook-idempotency.md) | Webhook verification/idempotency patterns |
| [`docs/tenant-isolation.md`](docs/tenant-isolation.md) | Tenant isolation foundation guidance |
| [`docs/observability-production.md`](docs/observability-production.md) | Observability foundation guidance |

## Local Development

These commands run the full app (foundation + appointment product routes):

Requirements: Python 3.13+, `uv`, Docker, Docker Compose, Make.

```bash
cp .env.example .env    # set a strong SECRET_KEY
make bootstrap          # compose up, migrate, seed, smoke the foundation app
make validate           # ruff + pytest with coverage floor
```

Useful commands:

| Command | Purpose |
|---------|---------|
| `make docker-up` / `make docker-down` | Start or stop the local Compose stack |
| `make migration-upgrade` | Apply inherited foundation migrations |
| `make seed-tenant` / `make seed` | Seed default tenant and development users |
| `make smoke` | Smoke test the inherited foundation API |
| `make validate-ai-workflows` | Validate AI workflow file presence |
| `make policy-guards` | Run CI policy guard scripts |
| `make validate` | Run foundation lint/tests/coverage |

Local URLs after startup:

| Resource | URL |
|----------|-----|
| API | http://localhost:8000 |
| OpenAPI / Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/health/ready |

Default inherited development login after seed:
`admin@example.local` / `devpassword123`. Change before shared environments.

## Project Structure

The current code structure is inherited from the foundation and will be extended
with Appointment Voice SaaS product modules in later implementation tasks.

| Path | Purpose |
|------|---------|
| [`app/api/`](app/api/) | FastAPI routes, dependencies, OpenAPI helpers |
| [`app/services/`](app/services/) | Service layer and domain errors |
| [`app/models/`](app/models/) | SQLAlchemy models |
| [`app/schemas/`](app/schemas/) | Pydantic schemas |
| [`app/core/`](app/core/) | Config, security, middleware, metrics |
| [`app/worker.py`](app/worker.py) | Background job consumer |
| [`alembic/`](alembic/) | Database migrations |
| [`tests/`](tests/) | Inherited foundation test suite |
| [`docs/`](docs/) | Product docs plus inherited foundation references |
| [`.ai-rules/`](.ai-rules/) | Binding AI/project rules |

## Next Implementation Step

Start with the product foundation tasks in
[`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md):

1. `AVS-A002` - Product architecture ADR for PostgreSQL source of truth,
   adapters, queue/outbox, idempotency, and tenancy.
2. `AVS-A003` - MVP demo flow definition.
3. `AVS-B001` - Business model as the first runtime slice.

Do not add booking logic, IVR, SMS, calendar, or frontend code before the core
domain model and migration/test pattern are established.
