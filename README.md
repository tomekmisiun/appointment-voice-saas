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

## What Is Implemented

As of Epic I / Epic J:

- **Appointment domain**: business, staff, service, working hours, availability engine, bookings with double-booking protection.
- **Notification outbox**: fake SMS provider (logs, marks delivered); real Twilio provider wired.
- **Calendar adapter**: fake calendar provider; real Google Calendar provider wired.
- **IVR simulation**: `/api/v1/ivr/simulate/*` — start call, press keys, book an appointment or transfer.
- **Call transfer**: press 2 in IVR → resolves to business phone or eligible staff.
- **Demo seed**: `make seed-demo` seeds a deterministic demo scenario (Glamour Studio Demo).
- **Smoke tests**: J001–J004 prove manual booking, IVR booking, cancellation, and demo seed locally.

## What Does Not Exist Yet

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
| `make seed-demo` | Seed the Glamour Studio Demo scenario (idempotent) |
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

## Demo Scenario (local)

```bash
# 1. Start stack and migrate
make docker-up migration-upgrade

# 2. Seed users + demo business (Glamour Studio Demo, 3 staff, 3 services, Mon–Sat hours)
make seed-tenant seed seed-demo

# 3. Log in
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.local","password":"devpassword123"}' | python3 -m json.tool

# 4. Simulate an IVR call (replace TOKEN and BUSINESS_ID)
curl -s -X POST http://localhost:8000/api/v1/ivr/simulate/call \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"business_id": BUSINESS_ID, "caller_phone": "+48600000001"}' | python3 -m json.tool

# 5. Press 1 to book, then 1 to select service, then 0 for any available
#    staff (the demo's 3 staff have no individual schedule, so they follow
#    the salon's hours and are all offered — press 1-3 to pick one by name
#    instead if you'd rather), then 1 to pick a slot (creates the booking)
curl -s -X POST http://localhost:8000/api/v1/ivr/simulate/press \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": SESSION_ID, "key": "1"}' | python3 -m json.tool

# 6. Or press 2 to transfer → returns action=TRANSFER + transfer_destination=+48100200300
```

Expected outputs:
- Booking created with `source=ivr`, `status=confirmed`.
- SMS notification in `notification_outbox` (fake provider logs to stdout).
- IVR transfer returns `{"action":"transfer","transfer_destination":"+48100200300"}`.

See `tests/test_avs_j001_seed_demo.py` through `test_avs_j004_smoke_cancellation.py`
for automated smoke assertions.

## Next Implementation Step

See [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) for
remaining tasks. Open items: AVS-A000 (roadmap cleanup), AVS-J006 (pilot
deployment checklist), and post-MVP epics (billing, frontend, real providers).
