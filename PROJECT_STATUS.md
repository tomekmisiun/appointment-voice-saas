# Project Status — Appointment Voice SaaS

This file records verified Appointment Voice SaaS status. It should not list
planned product capabilities as implemented.

## Current Status

- This product repository was created from an inherited production FastAPI
  backend foundation.
- Product planning docs exist.
- Appointment Voice SaaS runtime is not implemented yet.
- No product database models or migrations exist yet.
- No product IVR, SMS, calendar, booking, availability, call transfer, billing,
  or frontend implementation exists yet.
- Current next milestone: core product domain model.

## Verified Inherited Foundation Capabilities

The repository currently inherits these verified foundation capabilities:

- FastAPI app structure with versioned routes and standard middleware patterns.
- PostgreSQL, SQLAlchemy, Alembic setup, and migration tooling.
- Redis-backed rate limiting, cache, idempotency, and worker queue patterns.
- Auth, users, RBAC, tenant foundation, and tenant scoping patterns.
- Webhook verification and idempotency pattern.
- Background worker patterns with retries, delayed jobs, failed-job handling,
  and maintenance jobs.
- Observability, structured logging, request IDs, health checks, and metrics.
- Docker and Docker Compose local development stack.
- CI/testing/policy guards and coverage enforcement.
- AI workflow rules in `.ai-rules/`.

Detailed historical foundation status is preserved in
[`docs/foundation/template-project-status.md`](docs/foundation/template-project-status.md).

## Appointment Voice SaaS Verified Capabilities

Planning and architecture:

- Product scope documentation: [`docs/product-scope.md`](docs/product-scope.md).
- Domain vocabulary: [`docs/domain-model.md`](docs/domain-model.md).
- Product roadmap and executable backlog: [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
- Architecture ADR (PostgreSQL source of truth, adapters, outbox, tenancy): [`docs/adr/0002-appointment-voice-saas-architecture.md`](docs/adr/0002-appointment-voice-saas-architecture.md).
- Local demo flow script: [`docs/demo-flow.md`](docs/demo-flow.md).
- Technical debt/gap register: [`TECH_DEBT.md`](TECH_DEBT.md).

Core domain (EPIC B — merged 2026-06-14):

- **Business** model, service, schema, CRUD API (`/api/v1/businesses`).
- **Staff** model, service, schema, CRUD API (`/api/v1/businesses/{id}/staff`).
- **Service** model, service, schema, CRUD API (`/api/v1/businesses/{id}/services`).
- **WorkingHours** model, service, schema, API (`/api/v1/businesses/{id}/working-hours`).
- **AvailabilityException** model, service, schema, API (`/api/v1/businesses/{id}/availability-exceptions`).
- **Customer** model, service, schema with phone normalisation and race-safe deduplication.
- **Booking** model, service, schema with `CONFIRMED`/`CANCELLED` lifecycle.
- Alembic migrations for all domain tables with tenant indexes and FK constraints.
- PostgreSQL `EXCLUDE USING gist` constraint (`btree_gist`) for DB-level double-booking prevention.
- Booking creation, listing, read, and cancellation APIs (`/api/v1/businesses/{id}/bookings`).
- Cross-tenant isolation enforced at service layer (`require_business`, `require_staff`) for all nested writes.
- Cross-tenant isolation tests for all product tables (`tests/test_product_tenant_isolation.py`).

## Not Implemented Yet

- Availability engine (slot generation from working hours, booking exclusion, exception overlay, timezone handling, availability API).
- IVR runtime or local IVR simulation.
- Notification outbox, SMS provider interface, fake SMS adapter.
- Calendar provider interface, calendar event model, fake calendar adapter.
- Voice session model.
- Call transfer.
- Booking audit logs (AVS-D006).
- Working hours and availability exception HTTP route tests.
- Real provider integrations (Twilio, SMS, Google Calendar).
- Product smoke tests.
- Billing/subscriptions.
- Frontend.

## Next Implementation Milestone

**EPIC C — Availability engine** (`AVS-C001` to `AVS-C006`):

1. Slot generation from service duration and staff working hours.
2. Exclude slots overlapping existing confirmed bookings.
3. Apply availability exceptions (closures, special hours).
4. Correct timezone/DST handling per business.
5. Availability API endpoint.
6. Full availability test coverage.

See [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) for
the detailed task backlog.

## Rules For Updating This File

- Add only verified behavior here.
- Planned work belongs in [`ROADMAP.md`](ROADMAP.md) or
  [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
- Open gaps belong in [`TECH_DEBT.md`](TECH_DEBT.md).
- Product runtime capability requires code and tests before it is listed as
  verified.
