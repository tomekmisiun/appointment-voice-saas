# Roadmap — Appointment Voice SaaS

This is the high-level product roadmap. The detailed executable backlog lives in
[`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).

Historical inherited foundation roadmap:
[`docs/foundation/template-roadmap.md`](docs/foundation/template-roadmap.md).

## Product Goal

Build a mini SaaS for barbers and local service businesses that lose customers
when they miss phone calls. The target product answers calls with IVR, lets the
caller pick a service and available slot, creates the booking in PostgreSQL,
syncs through a calendar adapter, sends SMS confirmations/updates, and supports
business cancellation/reschedule plus optional call transfer to staff.

## Current State

- Product repository exists and inherits a production FastAPI foundation.
- Product planning docs and backlog exist.
- Appointment Voice SaaS runtime is not implemented yet.
- No product database models, migrations, booking engine, availability engine,
  IVR, SMS, calendar sync, transfer, billing, frontend, or product smoke tests
  exist yet.

## MVP Definition Of Done

The first working product is done when:

- A business/salon can exist in the system.
- Staff, services, working hours, and exceptions can be configured.
- Availability can be calculated with business timezone support.
- Booking can be created without double booking.
- Booking can be cancelled by the business.
- SMS notification intents exist for booking and cancellation.
- Calendar sync is represented through an adapter/outbox or fake provider.
- IVR flow can be simulated locally.
- A customer can select service and slot through IVR simulation.
- A booking is created from IVR simulation.
- Smoke test demonstrates the full simulated flow.
- Docs describe the local demo flow.

## Roadmap Phases

1. **Product documentation cleanup**
   - Make root docs product-first.
   - Preserve inherited foundation docs under `docs/foundation/`.
   - Keep status, roadmap, and debt focused on Appointment Voice SaaS.

2. **Core SaaS domain**
   - Business/salon, staff, service, working hours, availability exceptions,
     customer, and booking models.
   - Product migrations, indexes, and tenant isolation tests.

3. **Availability engine**
   - Generate slots from working hours.
   - Exclude bookings and exceptions.
   - Handle business timezone and DST cases.
   - Add availability API and tests.

4. **Booking engine with double-booking protection**
   - Booking creation service/API.
   - Booking list/read API.
   - Business cancellation.
   - DB-level concurrency protection.
   - Booking lifecycle audit logs and conflict tests.

5. **Notification outbox and fake SMS**
   - Product notification outbox.
   - SMS provider interface.
   - Fake SMS provider for local/dev/test.
   - Booking and cancellation notification intents.
   - Worker processing, retry/backoff, and DLQ behavior.

6. **Calendar adapter and fake provider**
   - Calendar provider interface.
   - Calendar integration and event records.
   - Fake calendar provider for local/dev/test.
   - Create/update/cancel calendar events from booking lifecycle.

7. **IVR simulation**
   - Voice session model.
   - Provider-neutral IVR response abstraction.
   - Local incoming-call simulation.
   - Service selection, slot proposal, booking confirmation, and no-slot paths.
   - End-to-end simulated IVR booking test.

8. **Real Twilio/SMS/calendar pilot**
   - Twilio voice adapter and signature validation.
   - Real SMS adapter and delivery status webhook.
   - Provider webhook idempotency and rate limiting.
   - Pilot provider runbook.

9. **Call transfer**
   - Business transfer settings.
   - Staff transfer eligibility.
   - IVR transfer branch and unavailable fallback.

10. **Production hardening**
    - Product smoke tests.
    - Monitoring and alerting for failed product integrations.
    - Retry/DLQ operations for SMS and calendar sync.
    - Pilot deployment checklist.

11. **Product expansion**
    - Reminder SMS.
    - Customer/business reschedule flows.
    - CRM clients and booking history.
    - Preferred staff.
    - Multi-service appointments.
    - Waitlist.
    - Dashboard metrics and CSV export.
    - Deposits/prepayments.
    - Billing/subscriptions.
    - Self-service onboarding.

## Next Recommended Execution Order

1. `AVS-A002` - Product architecture ADR.
2. `AVS-A003` - Demo flow definition.
3. `AVS-B001` - Business model.
4. `AVS-B002` - Staff model.
5. `AVS-B003` - Service model.
6. `AVS-B004` - Working hours model.
7. `AVS-B005` - Availability exceptions model.
8. `AVS-B006` - Customer model.
9. `AVS-B007` - Booking model.
10. `AVS-B008` - Core domain migrations and indexes.
11. `AVS-B009` - Tenant isolation tests for product tables.

After EPIC B is complete, continue with availability (`AVS-C001`) before booking
creation.

## Detailed Backlog

Use [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) as
the source of truth for task-level details, including scope, out of scope,
acceptance criteria, validation, and production risk.
