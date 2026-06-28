# ADR 0002: Appointment Voice SaaS Core Architecture

- **Status:** Accepted
- **Date:** June 2026
- **Roadmap:** AVS-A002

## Context

The Appointment Voice SaaS product is being built on top of an inherited
FastAPI/PostgreSQL/Redis foundation. Before implementing domain models, booking
engines, IVR flows, SMS, or calendar integrations, the core architectural
decisions must be recorded so all subsequent implementation follows consistent
rules.

The primary risk categories are:

- Double bookings: two callers simultaneously claiming the same staff/time slot.
- Tenant data leakage: product data from one business visible to another.
- Provider coupling: business logic embedded inside Twilio, Stripe, or Google
  Calendar clients instead of behind adapters.
- Silent async failures: SMS or calendar side effects that disappear without
  observability or retry.
- Timezone errors: bookings created or displayed in the wrong local time.

## Decisions

### 1. PostgreSQL is the booking source of truth

All appointment reservations are stored in PostgreSQL. Booking correctness is
enforced through database transactions and constraints (exclusive overlapping
booking indexes or row-level locks), not only through application-side
availability checks.

External calendars (Google Calendar and others) are integration views. They
must never decide whether a booking can be created, cancelled, or modified.
Calendar sync failures must not block or roll back booking creation.

### 2. Provider integrations are behind adapters

Every external provider (voice/IVR, SMS, calendar) must be accessed through a
provider-neutral interface defined in the application layer. The interface
contracts must be stable before any provider implementation is wired in.

Fake/stub provider implementations will be written first so that local
development and tests require no external accounts or network calls.

Real provider implementations (Twilio, real SMS, Google Calendar) are wired
behind the same interface and activated by configuration.

This means:

- `IVRProvider` / `SMSProvider` / `CalendarProvider` interfaces first.
- `FakeIVRProvider` / `FakeSMSProvider` / `FakeCalendarProvider` for local and
  test use.
- Real adapters added when provider integration tasks start (EPIC H).

### 3. Async side effects use outbox/queue/worker patterns

SMS notifications and calendar sync are async side effects. They must be
written to an outbox table or enqueued before the booking transaction commits.
They are processed by background workers using the existing worker/queue
infrastructure.

A failed SMS or calendar sync must not fail the booking itself. Failed
side-effect jobs are retried with backoff and routed to a dead-letter queue
after exhaustion.

### 4. Webhook handlers are idempotent

All inbound webhooks from voice, SMS, or calendar providers are idempotent by
provider message/event ID using the existing `IdempotencyRecord` pattern.
Duplicate webhook deliveries from provider retries must not create duplicate
bookings or messages.

### 5. Tenant isolation is mandatory for all product data

Every product table includes a tenant-scoped foreign key (business_id or
similar). Every query in services and repositories must filter by the current
tenant context. Cross-tenant reads and writes are blocked by tests
(`AVS-B009`). This follows the existing foundation tenancy patterns.

### 6. Phone numbers are masked in logs

Phone numbers (caller, customer, business) must never appear in plaintext in
log output or observability events. Use a masking helper (e.g., show last four
digits only) consistent with existing foundation privacy patterns.

### 7. Timezone is explicit per business

Every business has a configured timezone. All availability slot generation,
working hour comparisons, and booking time storage must handle timezone and DST
explicitly. Slot times are stored as timezone-aware UTC in PostgreSQL and
converted to local business timezone for display and availability logic.

## Alternatives Considered

### Calendar as source of truth (rejected)

Using Google Calendar or another external calendar as the booking source of
truth would introduce availability consistency risks (sync lag, provider
outages, two-way conflict handling). PostgreSQL transactions provide stronger
guarantees than external calendar APIs.

### Application-only double-booking prevention (rejected)

SELECT-then-INSERT with application-side duplicate checks are vulnerable to
race conditions under concurrent callers. The decision is to use
database-level exclusive constraints or advisory locks so that the DB rejects
duplicate inserts atomically.

### Synchronous SMS/calendar delivery (rejected)

Blocking API responses on external provider calls introduces latency, error
propagation, and cascading failures. The outbox/queue/worker pattern decouples
booking correctness from provider availability.

## Consequences

- All domain model implementation (EPIC B) must include tenant-scoped FK.
- Availability engine (EPIC C) must enforce timezone-aware slot generation.
- Booking engine (EPIC D) must use DB-level concurrency protection.
- Notification path (EPIC E) must write outbox before or within booking
  transaction.
- Calendar sync (EPIC F) must use the same worker/outbox pattern.
- IVR flow (EPIC G) must depend on adapter interface, not provider directly.
- Real provider integration (EPIC H) adds adapters behind existing interfaces.

## References

- `docs/architecture/domain-model.md`
- `docs/product/scope.md`
- `docs/project/implementation-backlog.md`
- `docs/adr/0001-sync-vs-async-architecture.md`
- `.ai-rules/tenancy.md`
- `.ai-rules/security.md`
- `.ai-rules/workers.md`
