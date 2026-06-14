# Project Status — Appointment Voice SaaS

This file records verified Appointment Voice SaaS status. It should not list
planned product capabilities as implemented.

## Current Status

Product backend **partially implemented** — see verified list below and
[`docs/learning/00-current-state-audit.md`](docs/learning/00-current-state-audit.md).

- Inherited FastAPI foundation: **running** (auth, tenants, worker, CI).
- Appointment domain (business → booking) + availability engine: **implemented**
  (code, migrations, tests).
- Notification outbox model, SMS provider interface, fake SMS adapter, and
  booking confirmation/cancellation enqueueing: **implemented** (`AVS-E001`–`AVS-E005`).
- IVR, calendar, transfer, frontend: **not implemented** (roadmap EPIC E–J).
- **Next milestone:** EPIC E — notification worker (`AVS-E006`).

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
- Booking audit logs for create/cancel lifecycle with actor and source (`tests/test_booking_audit.py`; AVS-D006).
- Cross-tenant isolation enforced at service layer (`require_business`, `require_staff`) for all nested writes.
- Cross-tenant isolation tests for all product tables (`tests/test_product_tenant_isolation.py`).

Availability engine (EPIC C — verified 2026-06-14):

- Slot generation from service duration and staff working hours (`app/services/availability_service.py`).
- Confirmed booking exclusion with half-open interval overlap check.
- Availability exception overlay: closures return empty; special hours override working hours.
- Correct timezone/DST handling via `zoneinfo.ZoneInfo` (Python 3.13 stdlib).
- Intra-tenant cross-business isolation: `service_id` and `staff_id` validated against `business_id`.
- Availability API endpoint (`GET /api/v1/businesses/{id}/availability`).
- Full availability test coverage (`tests/test_availability.py`; cross-business/cross-tenant isolation in `tests/test_product_tenant_isolation.py`).

Notifications outbox (EPIC E — verified 2026-06-14):

- `NotificationOutbox` model persisting SMS intent, recipient, template/purpose,
  status, and attempts before delivery (`app/models/notification_outbox.py`,
  migration `ad7b35681f01`, `AVS-E001`).
- Provider-neutral SMS send contract (`SmsMessage`, `SmsSendResult`) and
  `SmsProvider` protocol (`app/core/sms.py`, `app/services/sms_provider.py`, `AVS-E002`).
- `NullSmsProvider` (default, reports not configured) and `FakeSmsProvider`
  (records sent messages for local/dev/test use) (`AVS-E003`).
- Booking creation enqueues `BOOKING_CONFIRMATION` SMS intents for the
  customer, and for the business when it has a phone number
  (`app/services/notification_service.py`, `AVS-E004`).
- Booking cancellation enqueues `BOOKING_CANCELLATION` SMS intents for the
  customer, and for the business when it has a phone number
  (`app/services/notification_service.py`, `AVS-E005`).
- Test coverage in `tests/test_notification_outbox.py`, `tests/test_sms_provider.py`,
  and `tests/test_booking_notifications.py`.

## Not Implemented Yet

- IVR runtime or local IVR simulation.
- Notification worker to process and send queued outbox entries.
- Calendar provider interface, calendar event model, fake calendar adapter.
- Voice session model.
- Call transfer.
- Working hours and availability exception HTTP route tests.
- Real provider integrations (Twilio, SMS, Google Calendar).
- Product smoke tests.
- Billing/subscriptions.
- Frontend.

## Next Implementation Milestone

**EPIC E — Notifications outbox** (`AVS-E006` onwards):

See [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) for
the detailed task backlog.

## Rules For Updating This File

- Add only verified behavior here.
- Planned work belongs in [`ROADMAP.md`](ROADMAP.md) or
  [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
- Open gaps belong in [`TECH_DEBT.md`](TECH_DEBT.md).
- Product runtime capability requires code and tests before it is listed as
  verified.
