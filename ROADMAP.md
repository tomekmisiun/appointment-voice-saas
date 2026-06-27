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

Audit conducted 2026-06-27. All MVP foundation epics A–L are done. All P1
items are done. All P2 items are done except P2-013/014 (owner metrics, CSV
export). All P3 items are done except P3-007 (Stripe payment links, deliberately
deferred — not a priority for this portfolio project). P4-004 (self-service
signup) is done. P4-001/002/003 (systematic per-route tenancy audit/CI guard)
remain partially open.

A recovery audit on 2026-06-26 identified that telephony features
(`BusinessPhoneNumber` model, phone-number-based IVR routing, `telephony_status`
column), SAC-009 staff invitations, and SAC-006/007/008 staff lifecycle items
were developed on a contaminated branch and never merged to `main`. These are
tracked as new work — see Next Recommended Execution Order below. The production
database **may** have received the SAC-009 migration directly (unverified —
run `alembic current` against Railway to confirm before implementing SAC-009);
a no-op stub (`alembic/versions/sac009_staff_inv.py`) bridges the Alembic chain
regardless of outcome.

**Production (2026-06-27):** API returns 502 Bad Gateway — active blocker for
all production demos and pilot testing.

See [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md) for the full audit
snapshot and
[`docs/audits/AUDIT_CURRENT_REPO_STATE.md`](docs/audits/AUDIT_CURRENT_REPO_STATE.md)
for the 2026-06-27 audit report.

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

Updated 2026-06-27 to reflect completed P1–P3 work and recovery audit
findings. P3 is fully closed except P3-007 (deliberately deferred).

**Immediate blockers:**
1. Repair production API (502 Bad Gateway) — investigate Railway service logs.
2. Add `/demo` CTA to landing page (`frontend/src/app/page.tsx`).

**Required for real telephony (new work, extracted from recovery audit):**
3. `TELEPHONY-T1/T2` — `telephony_status` column on Business +
   `BusinessPhoneNumber` model and migration (from current head).
4. `TELEPHONY-T3` — Composite FK isolation for `BusinessPhoneNumber`.
5. `TELEPHONY-T4` — Seed demo phone number.
6. `TELEPHONY-T5` — Operator API (assign phone to business).
7. `TELEPHONY-T9` — Phone-number-based IVR routing (route Twilio webhooks
   by `To` field, not URL-embedded `business_id`).
8. `TELEPHONY-T6` — Telephony status card (frontend dashboard component).

**Independent tracks:**
9. `feat/sms-localization` — SMS messages are EN-only hardcoded; add
   locale-aware rendering per `business.language` (P3-009 IVR prompt
   architecture is the model).
10. `feat/public-booking-management-link` — HMAC-tokenized cancel/reschedule
    URL included in confirmation SMS.
11. `SAC-005` — Wire `BusinessMembership.role` into the authorization layer
    (currently `User.role` only; per-business RBAC is unimplemented).

**Staff lifecycle recovery (from backup snapshot — see recovery audit):**
12. `SAC-006` — Staff profile lifecycle (clean commit `a7bf6a1` in snapshot;
    extract after SAC-005 merges).
13. `SAC-007` / `SAC-008b` — Staff service assignments + composite FK
    isolation (extract after SAC-006 merges).
14. `SAC-009` — Staff invitations (HTTP routes do not yet exist; must not
    ship until `app/api/routes/staff_invitations.py` is added; verify
    production schema state with `alembic current` before migrating).
    See [`docs/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md`](docs/audits/MIXED_WORK_RECOVERY_AUDIT_2026-06-26.md)
    for the full extraction plan.

**Backlog (post-pilot):**
15. P2-013, P2-014 — Owner metrics API and CSV export.
16. Frontend configuration screens for services, working hours, recurring
    blocks, and availability exceptions.
17. P4-001/002/003 — Systematic per-route tenancy audit and CI guard.
18. P4-012 — Per-business IVR prompt customization.

## Detailed Backlog

Use [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md) as
the source of truth for task-level details, including scope, out of scope,
acceptance criteria, validation, and production risk.
