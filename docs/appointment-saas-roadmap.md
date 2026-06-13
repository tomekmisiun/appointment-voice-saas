# Appointment Voice SaaS Roadmap

Roadmap for turning this backend foundation into **Appointment Voice SaaS**.
This document is product bootstrap planning only. It does not describe runtime
booking code that exists today.

## Product Goal

Appointment Voice SaaS helps barbers and other local service businesses recover
missed-call revenue. A customer calls a business phone number, follows an
automated phone flow, chooses a service and available appointment slot, receives
SMS confirmation, and the business receives booking notification.

## MVP Scope

- Tenant-scoped business profile with service catalog and staff availability.
- Phone-session flow that can collect caller details, service choice, and slot
  choice through an IVR-style interaction.
- Booking creation with conflict prevention and clear lifecycle states.
- SMS confirmation to the customer and business after successful booking.
- Admin/API workflows for managing businesses, staff, services, working hours,
  availability exceptions, and bookings.
- Production-safe auditability, tenancy isolation, retries, and observability
  using the existing template patterns.

## Not In MVP

- AI voice agent or natural-language scheduling.
- Twilio, SMS provider, or calendar provider implementation before adapter
  boundaries are defined.
- Google Calendar sync.
- Call transfer to staff.
- SMS reminders beyond initial confirmation.
- Frontend application.
- Billing, subscriptions, invites, or marketplace features.
- Multi-location enterprise scheduling rules.

## Architecture Principles

- Keep product data tenant-scoped; a business belongs to one tenant.
- Put booking rules in services, not routes, and return domain errors through
  the existing error envelope.
- Model provider integrations behind adapters so Twilio, SMS, and calendar
  providers can be added without coupling core booking logic to vendors.
- Use database constraints and transactions for booking conflicts; do not rely
  only on application-side checks.
- Treat voice sessions, SMS messages, and calendar events as auditable workflow
  records with idempotency keys where providers may retry.
- Build thin vertical slices and validate with `make validate` before widening
  scope.

## Priority Definitions

| Tier | Meaning |
|------|---------|
| **P0** | Required before an internal MVP can create real bookings |
| **P1** | Required before a pilot business can use the product safely |
| **P2** | Needed for operational polish and broader local-service fit |
| **P3** | Later expansion or optional differentiation |

## Phase 0 - Product Bootstrap

**Status:** In progress.

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-000 | P0 | Capture product scope, domain vocabulary, and implementation roadmap | In progress |
| AVS-001 | P0 | Confirm MVP assumptions for first service vertical, starting with barbers | Not started |
| AVS-002 | P0 | Convert domain concepts into a technical design before model changes | Not started |

**Acceptance criteria:**

- `docs/product-scope.md` defines users, problem, MVP flow, non-goals, and
  assumptions.
- `docs/domain-model.md` defines the planned domain concepts without adding
  database models.
- This roadmap identifies phased work with task IDs, priorities, validation,
  and production risks.
- `PROJECT_STATUS.md` states that no appointment booking runtime code exists yet.

## Phase 1 - Core Domain Model

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-010 | P0 | Add tenant-scoped models for Business, Staff, Service, WorkingHours, AvailabilityException, Booking, and Customer | Not started |
| AVS-011 | P0 | Add migrations, indexes, uniqueness rules, and conflict-related constraints | Not started |
| AVS-012 | P0 | Add schemas and service-layer domain errors for booking-related entities | Not started |
| AVS-013 | P0 | Add tenancy and permission tests for all new domain entities | Not started |

**Acceptance criteria:**

- Models and migrations exist for core booking data with tenant isolation.
- Booking conflict invariants are documented and covered by tests.
- No provider-specific Twilio, SMS, calendar, AI, or frontend code is added.
- `make validate` and `make policy-guards` pass.

## Phase 2 - Booking API MVP

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-020 | P0 | Implement admin APIs for services, staff, working hours, exceptions, customers, and bookings | Not started |
| AVS-021 | P0 | Implement availability query service for bookable slots | Not started |
| AVS-022 | P0 | Implement booking creation, cancellation, and status transitions | Not started |
| AVS-023 | P1 | Add audit logs and operational metrics for booking writes | Not started |

**Acceptance criteria:**

- A tenant admin can configure service duration, staff schedules, and exceptions.
- Availability responses exclude unavailable staff/time combinations.
- Booking creation prevents double booking under concurrent requests.
- API behavior is covered by unit and integration tests.
- `make validate` and `make policy-guards` pass.

## Phase 3 - Voice Flow and Notification Boundaries

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-030 | P0 | Define VoiceSession lifecycle and IVR state machine independent of Twilio | Not started |
| AVS-031 | P0 | Add provider-neutral inbound-call and keypad-input adapter contracts | Not started |
| AVS-032 | P0 | Add SMSMessage outbox model and provider-neutral notification service | Not started |
| AVS-033 | P1 | Add retry, idempotency, and DLQ behavior for notification jobs | Not started |

**Acceptance criteria:**

- Voice flow can be exercised through tests without a real telephony provider.
- SMS confirmation intent is persisted before provider delivery is attempted.
- Provider retries cannot create duplicate bookings or duplicate final messages.
- Runtime vendor integration remains behind adapters.
- `make validate` and `make policy-guards` pass.

## Phase 4 - Pilot Integrations

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-040 | P1 | Add Twilio voice webhook adapter for the provider-neutral voice flow | Not started |
| AVS-041 | P1 | Add SMS provider adapter for confirmation delivery | Not started |
| AVS-042 | P1 | Add production runbook for phone numbers, webhook secrets, retries, and incident response | Not started |
| AVS-043 | P1 | Add pilot-readiness smoke checks for call-to-booking flow | Not started |

**Acceptance criteria:**

- A pilot business can receive a test call that creates a booking and sends
  confirmations.
- Webhook signatures, replay protection, rate limits, and idempotency are
  enforced.
- Provider credentials are environment-driven and documented without secrets.
- `make validate`, `make policy-guards`, and provider smoke checks pass.

## Phase 5 - Post-MVP Expansion

| Task ID | Priority | Task | Status |
|---------|----------|------|--------|
| AVS-050 | P2 | Add SMS reminders and configurable reminder windows | Not started |
| AVS-051 | P2 | Add call transfer to staff during business hours | Not started |
| AVS-052 | P2 | Add Google Calendar sync adapter and CalendarEvent reconciliation | Not started |
| AVS-053 | P3 | Add optional AI voice agent for natural-language booking | Not started |
| AVS-054 | P3 | Add frontend/admin portal | Not started |

**Acceptance criteria:**

- Expansion features remain optional and do not compromise core booking
  correctness.
- Calendar sync is idempotent and handles provider outages.
- AI voice features cannot bypass booking conflict checks.
- `make validate`, `make policy-guards`, and integration-specific checks pass.

## Validation Commands

Use the existing template validation commands:

```bash
make validate-ai-workflows
make policy-guards
make validate
```

For documentation-only changes, `make validate-ai-workflows` and
`make policy-guards` are the expected checks. Run `make validate` when docs
claim changed runtime behavior, test counts, APIs, migrations, or dependencies.

## Production Risks

- **Missed or duplicate bookings:** booking creation must be transactional and
  concurrency-tested before real businesses use it.
- **Tenant data leakage:** every product table and query must preserve tenant
  isolation.
- **Provider retry behavior:** voice, SMS, and calendar webhooks can retry and
  arrive out of order; idempotency is mandatory.
- **Phone-flow abandonment:** incomplete calls must not reserve slots forever.
- **Timezone and daylight-saving errors:** working hours and availability must
  use explicit business timezones.
- **SMS compliance:** consent, opt-out, message content, and regional rules must
  be handled before production messaging.
- **Operational visibility:** failed calls, failed notifications, and booking
  conflicts need logs, metrics, and alertable signals.
