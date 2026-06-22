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

See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) for the verified, evidence-backed
current state and
[`docs/audits/p3-remaining-backlog-audit.md`](docs/audits/p3-remaining-backlog-audit.md)
for what's left. Summary: the full MVP foundation (phases 1–9 below), all of
the P1 backlog, all of P2 except owner metrics/CSV export (P2-013/014), and
7 of 14 P3 operational-extension items are implemented and tested. Remaining
work is the rest of phase 11
(deposits/billing, calendar privacy/two-way-sync ADRs, integration
reconciliation, dashboard metrics/CSV export, self-service onboarding) — see
phase 11 below and the backlog file for task-level detail.

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

Phases 1–9 (foundation through call transfer) and most of phase 11 (product
expansion) are done — see `PROJECT_STATUS.md`. Remaining work, per
`docs/audits/p3-remaining-backlog-audit.md` §6:

1. `feat/p3-013-reconciliation-job` — no dependency on any other remaining
   item; can land in parallel with the deposits track.
2. `docs/adr-deposits-architecture` (P3-006) — ADR only, unblocks P3-007/008.
3. `docs/adr-calendar-import-spike` (P3-011) — ADR/spike only.
4. `docs/adr-two-way-calendar-sync` (P3-014) — depends on #3.
5. `feat/p3-010-calendar-visibility` — depends on #3.
6. `feat/p3-007-stripe-payment-links` — depends on #2.
7. `feat/p3-008-pending-payment-state` — depends on #6.
8. P2-013/014 (owner metrics, CSV export) and P4-001 through P4-011
   (tenancy hardening, onboarding, billing) remain sequenced after the P3
   operational-extensions tier.

## Detailed Backlog

Use [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) as
the source of truth for task-level details, including scope, out of scope,
acceptance criteria, validation, and production risk.
