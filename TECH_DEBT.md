# Technical Debt — Appointment Voice SaaS

This is the active product technical debt and gap register. Do not mark product
items Done unless Appointment Voice SaaS runtime code and tests exist.

Historical inherited foundation debt is preserved in
[`docs/foundation/template-tech-debt.md`](docs/foundation/template-tech-debt.md).

**Status legend:** Open | In Progress | Done

## Critical Product Gaps

| ID | Issue | Impact | Recommendation | Priority | Related roadmap task | Effort | Status |
|----|-------|--------|----------------|----------|----------------------|--------|--------|
| AVS-TD-001 | No core product domain models. | The product cannot represent businesses, staff, services, hours, customers, bookings, voice sessions, notifications, or calendar events. | Implement the core SaaS domain models, schemas, services, migrations, indexes, and tenant isolation tests. | Critical | AVS-B001 to AVS-B009 | L | Done |
| AVS-TD-002 | No appointment availability engine. | Customers cannot see valid bookable slots. | Build slot generation from working hours, bookings, exceptions, and business timezone. | Critical | AVS-C001 to AVS-C006 | L | Done |
| AVS-TD-003 | No booking creation flow. | The product cannot create appointments. | Implement booking service/API and booking lifecycle state. | Critical | AVS-D001, AVS-D003, AVS-D004 | L | Done |
| AVS-TD-004 | No DB-level double-booking protection for appointments. | Concurrent callers or admins could book the same staff and slot. | Enforce booking conflict protection with database transactions/constraints and concurrency tests. | Critical | AVS-D002, AVS-D007 | L | Done |
| AVS-TD-005 | No notification outbox for product SMS/calendar side effects. | Confirmations and calendar sync can be lost or coupled to request handling. | Add product outbox/worker path for SMS and calendar side effects. | Critical | AVS-E001, AVS-E004 to AVS-E008, AVS-F005 to AVS-F007 | XL | Open |
| AVS-TD-006 | No IVR runtime or simulation flow. | The phone-first product cannot be developed or demoed locally. | Build provider-neutral voice session and local IVR simulation before real Twilio. | Critical | AVS-G001 to AVS-G010 | L | Open |
| AVS-TD-007 | No product smoke test. | The full simulated booking flow cannot be verified end to end. | Add deterministic manual, IVR, booking, cancellation, fake SMS, and fake calendar smoke tests. | Critical | AVS-J002 to AVS-J004 | M | Open |
| AVS-TD-008 | No product calendar adapter. | Bookings cannot be represented in a calendar integration. | Add calendar provider interface, integration model, event table, and fake calendar provider. | Critical | AVS-F001 to AVS-F004 | L | Open |
| AVS-TD-009 | No product-specific tenant isolation tests. | Product tables/APIs may leak data across businesses or tenants once implemented. | Add cross-tenant denial tests for every product model and API. | Critical | AVS-B009, P4-001 to P4-003 | M | Done |

## High Product Gaps

| ID | Issue | Impact | Recommendation | Priority | Related roadmap task | Effort | Status |
|----|-------|--------|----------------|----------|----------------------|--------|--------|
| AVS-TD-010 | No reminder SMS. | No-show reduction is weaker for pilot businesses. | Add scheduled reminder intents and worker delivery. | High | P1-001 | M | Open |
| AVS-TD-011 | No reschedule flow. | Customers and businesses cannot move appointments without manual work. | Implement customer IVR reschedule and business/admin reschedule with SMS/calendar updates. | High | P1-003, P1-004 | L | Open |
| AVS-TD-012 | No IVR timeout or invalid-input fallback. | Callers can get stuck, abandon calls, or trigger incorrect state. | Add timeout, invalid input, repeat menu, and backend-unavailable fallback. | High | P1-005 to P1-008 | M | Open |
| AVS-TD-013 | No real SMS provider. | Pilot confirmations cannot be delivered outside local fake provider. | Add provider adapter, status webhook, idempotency, and delivery monitoring. | High | AVS-H003, AVS-H004, AVS-H005 | M | Open |
| AVS-TD-014 | No real voice provider. | Live callers cannot use the IVR. | Add Twilio voice webhook adapter, signature validation, and provider runbook. | High | AVS-H001, AVS-H002, AVS-H007 | M | Open |
| AVS-TD-015 | No SMS/calendar retry/DLQ for product side effects. | Failed notifications or calendar updates can disappear silently. | Add retry/backoff, DLQ, and alerting for product side effects. | High | AVS-E007, AVS-F007, P1-009 to P1-011 | M | Open |
| AVS-TD-016 | No product monitoring/alerting. | Pilot failures may not be visible. | Add metrics/logs/alerts for booking failures, IVR failures, SMS failures, and calendar sync failures. | High | P1-012, AVS-J006 | M | Open |

## Medium Product Gaps

| ID | Issue | Impact | Recommendation | Priority | Related roadmap task | Effort | Status |
|----|-------|--------|----------------|----------|----------------------|--------|--------|
| AVS-TD-017 | No CRM clients table. | Returning-customer history and personalization are limited. | Add basic CRM clients and link bookings to clients. | Medium | P2-001, P2-002 | M | Open |
| AVS-TD-018 | No preferred staff flow. | Customers cannot choose or reuse preferred staff. | Add preferred staff selection and last-staff suggestion. | Medium | P2-006, P2-007 | M | Open |
| AVS-TD-019 | No multi-service appointment support. | Combined services cannot be booked as one appointment. | Add multi-service booking model and combined-duration availability. | Medium | P2-008, P2-009 | L | Open |
| AVS-TD-020 | No waitlist. | Fully booked businesses cannot recover demand after cancellations. | Add waitlist model, offer flow, and timeout/escalation. | Medium | P2-010 to P2-012 | L | Open |
| AVS-TD-021 | No dashboard metrics. | Business owners cannot see booking volume or missed-call conversion. | Add tenant-safe owner metrics API. | Medium | P2-013 | M | Open |
| AVS-TD-022 | No salon hours versus staff hours intersection. | Availability cannot distinguish business closures from staff schedules. | Add salon hours, closure exceptions, staff blocks, and intersection logic. | Medium | P3-001 to P3-005 | M | Open |

## Future Product Gaps

| ID | Issue | Impact | Recommendation | Priority | Related roadmap task | Effort | Status |
|----|-------|--------|----------------|----------|----------------------|--------|--------|
| AVS-TD-023 | No deposits/prepayments. | Businesses cannot reduce no-shows with deposits. | Write payment architecture ADR before Stripe payment links or pending-payment holds. | Future | P3-006 to P3-008 | L | Open |
| AVS-TD-024 | No multilingual IVR. | Non-English callers would require duplicated prompt logic later. | Add prompt-key architecture before translation content. | Future | P3-009 | M | Open |
| AVS-TD-025 | No staff private calendar OAuth/sync policy. | Calendar integration could leak private staff event details. | Define busy/free-only rules and privacy tests before advanced calendar sync. | Future | P3-010, P3-011, P3-014 | L | Open |
| AVS-TD-026 | No SaaS onboarding. | Salon setup and phone provisioning remain manual. | Add self-service salon onboarding, wizard APIs, and phone provisioning workflow. | Future | P4-004 to P4-006 | L | Open |
| AVS-TD-027 | No Stripe Billing/subscriptions. | The SaaS cannot enforce paid plans or subscription limits. | Add billing model, webhooks, plans, limits, and compatibility checklist after product MVP. | Future | P4-007 to P4-011 | L | Open |

## Update Rules

- Keep this file focused on Appointment Voice SaaS product gaps.
- Do not add inherited foundation debt here; use `docs/foundation/` for
  foundation reference material.
- Mark an item Done only when product runtime code and tests verify the fix.
- Planned implementation details belong in
  [`docs/appointment-saas-roadmap.md`](docs/appointment-saas-roadmap.md).
