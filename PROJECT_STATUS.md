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

Verified product capabilities today:

- Product scope documentation exists:
  [`docs/product-scope.md`](docs/product-scope.md).
- Domain vocabulary documentation exists:
  [`docs/domain-model.md`](docs/domain-model.md).
- Product roadmap and executable backlog exist:
  [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
- Product technical debt/gap register exists:
  [`TECH_DEBT.md`](TECH_DEBT.md).

No runtime booking capabilities are implemented yet.

## Not Implemented Yet

- Business/salon, staff, service, working hours, availability exception,
  customer, booking, voice session, notification outbox, SMS message, calendar
  integration, or calendar event product models.
- Product migrations for appointment scheduling.
- Availability engine.
- Booking creation, cancellation, reschedule, or double-booking protection.
- Appointment APIs.
- IVR runtime or local IVR simulation.
- SMS provider integration or fake SMS product adapter.
- Calendar sync or fake calendar product adapter.
- Call transfer.
- Product smoke tests.
- Billing/subscriptions.
- Frontend.

## Next Implementation Milestone

Recommended implementation sequence:

1. Core SaaS domain models and migrations.
2. Availability engine.
3. Booking engine with DB-level double-booking protection.
4. Notification outbox and fake SMS.
5. IVR simulation.
6. Calendar adapter and fake provider.
7. Real provider integrations for pilot.

Start with:

- `AVS-A002` - Product architecture ADR.
- `AVS-A003` - Demo flow definition.
- `AVS-B001` - Business model.

See [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) for
the detailed task backlog.

## Rules For Updating This File

- Add only verified behavior here.
- Planned work belongs in [`ROADMAP.md`](ROADMAP.md) or
  [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
- Open gaps belong in [`TECH_DEBT.md`](TECH_DEBT.md).
- Product runtime capability requires code and tests before it is listed as
  verified.
