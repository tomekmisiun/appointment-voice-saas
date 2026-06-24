# Appointment Voice SaaS Roadmap

This is the product roadmap for turning the current FastAPI backend foundation
into a working **Appointment Voice SaaS** product. It separates verified
foundation capabilities from planned product runtime work.

## Current repository reality

Updated 2026-06-17 (audit/backlog-reality-check). All MVP foundation epics A–K
are implemented. 638 tests pass, CI green.

Verified implemented: FastAPI + PostgreSQL foundation, core SaaS domain (Business,
Staff, Service, WorkingHours, AvailabilityException, Customer, Booking), availability
engine with timezone/DST tests, DB-level double-booking constraint (btree_gist EXCLUDE),
notification outbox + fake/real SMS, calendar adapter + fake provider + worker, IVR
simulation harness, full booking flow via IVR, Twilio voice/SMS real provider adapters,
Twilio signature validation, call transfer (business_phone and staff policies),
transfer unavailable fallback, demo seed script, smoke tests, booking_mode/subscription_plan
dimensions, exponential retry backoff, DLQ infrastructure, booking lifecycle audit logs.

Not implemented: SMS reply handling, reschedule, DLQ alerting integration,
CRM, waitlist, billing, frontend.

## Product goal

Build a mini SaaS for barbers and other local service businesses that miss calls
while serving customers. The target flow is:

1. A customer calls the business phone number.
2. IVR answers.
3. The customer selects a service.
4. The customer selects an available appointment slot.
5. The backend creates a booking in PostgreSQL.
6. The booking is synced to a calendar through an adapter/outbox.
7. SMS confirmation goes to the customer and business.
8. The business can cancel or reschedule.
9. SMS cancellation/change messages are sent.
10. The customer can press 2 to transfer to staff when transfer is enabled and
    staff accepts the call.

## Definition of done for first working product

The first working product is done when:

- A business/salon can exist in the system.
- Staff can be configured.
- Services can be configured.
- Working hours and exceptions can be configured.
- Availability can be calculated.
- Booking can be created without double booking.
- Booking can be cancelled by the business.
- SMS notification intents exist for booking and cancellation.
- IVR flow can be simulated locally.
- Customer can select service and slot through IVR simulation.
- Booking is created from IVR simulation.
- Calendar sync is represented through an adapter/outbox or fake provider.
- Smoke test demonstrates the full simulated flow.
- Docs describe the local demo flow.

## Architecture principles

- PostgreSQL is the source of truth for bookings.
- External calendar is an integration/view, not the source of truth.
- Provider integrations must be behind adapters.
- Async side effects must use queue/outbox/worker patterns.
- Booking correctness must be enforced with DB transactions/constraints, not
  only Python checks.
- Webhook handlers must be idempotent.
- Tenant isolation is mandatory for every product table and query.
- Phone numbers must be masked in logs.
- Timezone handling must be explicit per business.

## Task field guide

Each backlog row is intentionally executable:

- **Goal:** the outcome of the task.
- **Scope:** what to build or document.
- **Out:** explicit out of scope.
- **Acceptance:** what must be true before the task is complete.
- **Validation:** expected checks for that task.
- **Risk:** main production risk if the task is incomplete or wrong.

## MVP foundation backlog: current repo to working base product

All MVP epics completed (2026-06-16). Original execution order (completed):

1. `AVS-A002` – Architecture ADR ✓
2. `AVS-A003` – Demo flow definition ✓
3. `AVS-B001`–`AVS-B009` – Core SaaS domain ✓
4. `AVS-C001`–`AVS-C006` – Availability engine ✓
5. `AVS-D001`–`AVS-D007` – Booking engine ✓
6. `AVS-E001`–`AVS-E008` – Notification outbox and fake SMS ✓
7. `AVS-F001`–`AVS-F007` – Calendar adapter ✓
8. `AVS-G001`–`AVS-G010` – IVR simulation ✓
9. `AVS-H001`–`AVS-H007` – Real provider integrations ✓
10. `AVS-I001`–`AVS-I005` – Call transfer ✓
11. `AVS-J001`–`AVS-J006` – Demo and MVP readiness ✓
12. `AVS-K001` – Booking mode and subscription plan ✓
13. `AVS-L001` – Owner lead intake (manual pilot onboarding) ✓
14. `AVS-L002` – Manual pilot onboarding runbook ✓
15. `AVS-L003` – Owner dashboard skeleton (scope doc + API gap analysis) ✓
16. `AVS-L004` – Self-service onboarding API ✓

Remaining work: P1–P4 production expansion backlog.

### EPIC A - Product foundation from template

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-A000 | P0 | Clean up bootstrap status. | Align roadmap, status, README, and debt docs. | Runtime code. | Docs clearly separate foundation from planned product runtime. | `make validate-ai-workflows`, `make policy-guards`. | False readiness claims mislead implementation. |
| [x] | AVS-A001 | P0 | Align product fork naming/status. | Review README/status wording for Appointment Voice SaaS transition. | Renaming packages or env defaults. | Readers know this is a foundation transitioning to product. | Docs review, policy guards. | Operators confuse template features with product features. |
| [x] | AVS-A002 | P0 | Record core architecture decision. | ADR for PostgreSQL source of truth, adapters, queue/outbox, idempotency, tenancy. | Implementing models/adapters. | ADR accepted before domain implementation starts. | Docs review, policy guards. | Later integrations bypass core booking invariants. |
| [x] | AVS-A003 | P0 | Define MVP demo flow. | Document local simulated call-to-booking-to-notification-to-calendar scenario. | Real Twilio/SMS/calendar. | Demo script steps and expected records are described. | Docs review, later smoke test. | Team builds tasks without a shared product target. |

### EPIC B - Core SaaS domain

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-B001 | P0 | Add Business model. | Tenant-scoped business/salon identity, timezone, phone metadata. | Staff/service logic. | Model, schema, service, CRUD/API path, tests. | `make validate`, migration checks. | Missing tenant/timezone basis breaks all scheduling. |
| [x] | AVS-B002 | P0 | Add Staff model. | Tenant/business-scoped staff with active status and contact fields. | Transfer logic. | Staff can be created/read/updated/deactivated per business. | `make validate`. | Staff data leaks or stale staff remain bookable. |
| [x] | AVS-B003 | P0 | Add Service model. | Business-scoped services with duration, active status, optional price metadata. | Multi-service bookings. | Active services can drive slot duration. | `make validate`. | Bad durations create impossible availability. |
| [x] | AVS-B004 | P0 | Add WorkingHours model. | Recurring local day/time windows for staff/business. | Holiday exceptions. | Working hours validate time ranges and timezone assumptions. | `make validate`. | Availability generated from invalid schedules. |
| [x] | AVS-B005 | P0 | Add AvailabilityException model. | One-off closed/open windows for staff/business. | Recurring blocks. | Exceptions can override normal working hours. | `make validate`. | Closures or blocks are ignored. |
| [x] | AVS-B006 | P0 | Add Customer model. | Business-scoped customer with normalized phone and optional name. | CRM history UI. | Customers dedupe by phone within business. | `make validate`. | Duplicate customers and privacy errors. |
| [x] | AVS-B007 | P0 | Add Booking model. | Business/customer/service/staff/time/status/source fields. | Calendar/SMS delivery. | Booking stores start/end/status and lifecycle metadata. | `make validate`. | Booking records cannot support lifecycle/audit. |
| [x] | AVS-B008 | P0 | Add domain migrations/indexes. | Alembic revisions, FKs, tenant indexes, uniqueness and conflict indexes. | Destructive migration. | Migrations upgrade/downgrade cleanly; indexes cover core queries. | `make validate`, migration tests. | Slow or unsafe booking queries. |
| [x] | AVS-B009 | P0 | Add tenant isolation tests. | Cross-tenant denial/list/read/write tests for product tables. | Full product API coverage. | Product data cannot be accessed across tenants. | `make validate`. | Cross-tenant data leakage. |

### EPIC C - Availability engine

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-C001 | P0 | Generate slots from working hours. | Slot generation from service duration and staff schedule. | Existing booking exclusion. | Slots align to local business schedule. | Unit tests, `make validate`. | Customers see impossible slots. |
| [x] | AVS-C002 | P0 | Exclude existing bookings. | Remove slots overlapping active bookings. | DB-level conflict enforcement. | Availability excludes booked staff/time ranges. | Unit/integration tests. | Double-booking shown as available. |
| [x] | AVS-C003 | P0 | Exclude exceptions. | Apply closures, blocks, and special hours. | Recurring staff blocks. | Exceptions override normal slot generation. | Unit/integration tests. | Closed times remain bookable. |
| [x] | AVS-C004 | P0 | Support business timezone. | Explicit timezone input/output and DST edge cases. | Multi-timezone staff. | Availability is correct across DST transitions. | Timezone tests, `make validate`. | Off-by-one-hour bookings. |
| [x] | AVS-C005 | P0 | Add Availability API. | Tenant-scoped endpoint for service/staff/date availability. | Booking creation. | API returns bookable slots with stable contract. | API tests, `make validate`. | Clients depend on unstable availability contract. |
| [x] | AVS-C006 | P0 | Cover availability behavior. | Unit and integration tests for C001-C005. | Load testing. | Empty, full, exception, timezone, and tenant cases pass. | `make validate`. | Edge cases regress silently. |

### EPIC D - Booking engine

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-D001 | P0 | Add booking creation service. | Validate business, staff, service, customer, slot, and status. | SMS/calendar side effects. | Service creates valid booking in one transaction. | Unit/integration tests. | Invalid bookings enter source of truth. |
| [x] | AVS-D002 | P0 | Prevent double booking in DB. | Constraints/transaction strategy for overlapping staff bookings. | Calendar conflict source of truth. | Concurrent creates cannot double-book same staff/slot. | Concurrency tests, `make validate`. | Revenue-impacting duplicate bookings. |
| [x] | AVS-D003 | P0 | Add booking creation API. | Tenant/admin or system endpoint for creating bookings. | IVR endpoint. | API returns booking or conflict error envelope. | API tests. | Clients cannot create bookings consistently. |
| [x] | AVS-D004 | P0 | Add booking list/read API. | Tenant-scoped listing, filtering, and single read. | Dashboard metrics. | Business can inspect bookings. | API tests. | Staff cannot verify schedule. |
| [x] | AVS-D005 | P0 | Add business cancellation. | Cancel booking with reason and lifecycle state. | Customer self-cancel. | Cancelled booking no longer blocks active availability if policy allows. | API/service tests. | Cancelled slots remain stuck or audit is missing. |
| [x] | AVS-D006 | P1 | Add booking audit logs. | Audit lifecycle changes and actor/source. | Full compliance export. | Create/cancel state changes are auditable. | Tests, existing audit patterns. | Disputes cannot be investigated. |
| [x] | AVS-D007 | P0 | Add conflict/concurrency tests. | Race tests for same staff/time and cancellation behavior. | Load benchmark. | Tests prove DB-level double-booking protection. | `make validate`. | Python-only checks fail under concurrency. |

### EPIC E - Notification outbox and fake SMS

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-E001 | P0 | Add notification outbox model. | Persist SMS intent, recipient, template/purpose, status, attempts. | Real SMS provider. | Intent is stored before delivery attempt. | Migration/tests. | Lost confirmations on worker/provider failure. |
| [x] | AVS-E002 | P0 | Add SMS provider interface. | Provider-neutral send contract and result mapping. | Twilio implementation. | Code can send through fake or real adapter later. | Unit tests. | Business logic couples to one vendor. |
| [x] | AVS-E003 | P0 | Add fake SMS provider. | Local/dev/test provider that records messages. | Real delivery. | Tests can assert sent/intended messages without network. | Unit/integration tests. | Local demos require paid provider. |
| [x] | AVS-E004 | P0 | Enqueue booking confirmation SMS. | Customer and business confirmation intents after booking. | Reminder SMS. | Booking create enqueues expected intents idempotently. | Service tests. | Bookings happen without notification. |
| [x] | AVS-E005 | P0 | Enqueue cancellation SMS. | Customer and business cancellation/change intent. | Reschedule messages. | Cancellation enqueues expected intents. | Service tests. | Cancelled appointments are not communicated. |
| [x] | AVS-E006 | P0 | Add notification worker. | Use existing worker pattern to process outbox/send jobs. | Separate queue system. | Worker transitions pending/sent/failed statuses. | Worker tests. | Side effects block API or disappear. |
| [x] | AVS-E007 | P1 | Add retry/backoff/DLQ. | Retry failed sends and route exhausted attempts to DLQ. | Provider status webhooks. | Failed notifications are recoverable/visible. | Worker tests. | Silent notification loss. |
| [x] | AVS-E008 | P0 | Cover notification behavior. | Outbox, fake provider, enqueue, worker tests. | Provider certification. | Happy path and failure path pass. | `make validate`. | Async notification path regresses. |

### EPIC F - Calendar adapter foundation

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-F001 | P0 | Add calendar provider interface. | Provider-neutral create/update/cancel contract. | Google OAuth. | Booking code depends on interface only. | Unit tests. | Calendar provider dictates domain design. |
| [x] | AVS-F002 | P0 | Add calendar integration model. | Business/staff calendar settings and fake provider config. | Real OAuth tokens. | Business can have configured calendar integration state. | Migration/tests. | Sync runs without known destination. |
| [x] | AVS-F003 | P0 | Add calendar event table. | Map booking to provider event/status/errors. | Two-way sync. | Calendar event record tracks sync lifecycle. | Migration/tests. | Duplicate or orphaned calendar events. |
| [x] | AVS-F004 | P0 | Add fake calendar provider. | Local/dev/test provider storing fake events. | Real Google Calendar. | Demo and tests can verify sync without network. | Unit/integration tests. | Calendar path cannot be tested locally. |
| [x] | AVS-F005 | P0 | Create calendar event after booking. | Enqueue/create fake calendar event from booking. | External calendar as source of truth. | Booking produces event intent/result. | Worker/service tests. | Business calendar misses bookings. |
| [x] | AVS-F006 | P1 | Cancel/update calendar event. | Reflect cancellation/reschedule in calendar adapter. | Two-way external updates. | Cancellation updates fake calendar event state. | Worker/service tests. | Calendar diverges after lifecycle changes. |
| [x] | AVS-F007 | P1 | Cover calendar retry/DLQ. | Retry/backoff/DLQ tests for sync failures. | Real provider status polling. | Failed sync is visible and retryable. | Worker tests. | Calendar failures remain silent. |

### EPIC G - Voice/IVR simulation before real provider

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-G001 | P0 | Add VoiceSession model. | Session state, caller phone, selections, expiry, linked booking. | Real Twilio call SID handling. | Session can persist simulated IVR progress. | Migration/tests. | IVR state is lost or duplicated. |
| [x] | AVS-G002 | P0 | Add IVR response abstraction. | Provider-neutral prompts, keypad options, redirect/end/transfer intents. | TwiML adapter. | Simulation and future providers share flow contract. | Unit tests. | Voice flow locks into one provider. |
| [x] | AVS-G003 | P0 | Add incoming call simulation harness. | Local endpoint/test helper to start a voice session. | Public webhook. | Developer can simulate inbound call locally. | API/test harness tests. | No local E2E path. |
| [x] | AVS-G004 | P0 | Add main menu. | Book appointment or transfer to staff option. | Real transfer. | Press 1 books; press 2 follows transfer branch placeholder. | IVR tests. | Callers cannot reach intended workflow. |
| [x] | AVS-G005 | P0 | Add service keypad selection. | Map keypad input to active services. | Speech recognition. | Caller can select configured service. | IVR tests. | Wrong service booked. |
| [x] | AVS-G006 | P0 | Add slot proposal keypad flow. | Present available slots and accept keypad choice. | Arbitrary date search. | Caller can select a generated slot. | IVR tests. | Caller cannot complete booking. |
| [x] | AVS-G007 | P0 | Confirm booking from IVR. | Create booking from selected service/slot/customer. | SMS/calendar provider delivery. | Simulated IVR creates booking through booking service. | E2E IVR test. | IVR bypasses booking correctness. |
| [x] | AVS-G008 | P0 | Handle no available slots. | Prompt/end/fallback path when no slots exist. | Waitlist. | No-slot case is clear and does not create booking. | IVR tests. | Bad user experience or invalid booking. |
| [x] | AVS-G009 | P1 | Add voice session expiration. | Expire incomplete sessions and release pending state. | Long-term analytics. | Old sessions cannot complete stale booking. | Worker/service tests. | Stale sessions create wrong bookings. |
| [x] | AVS-G010 | P0 | Add E2E IVR simulation test. | Full simulated call, service, slot, booking, fake SMS, fake calendar. | Real provider smoke. | One test demonstrates local product flow. | `make validate`. | MVP cannot be verified end to end. |

### EPIC H - Real provider integrations for pilot

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-H001 | P1 | Add Twilio voice webhook adapter. | Convert Twilio requests/responses to provider-neutral IVR contract. | AI voice. | Twilio can drive existing IVR flow. | Adapter/API tests. | Provider details leak into domain logic. |
| [x] | AVS-H002 | P1 | Validate voice webhook signatures. | Verify Twilio signatures and reject invalid requests. | IP allowlisting only. | Invalid signatures fail consistently. | Security tests. | Spoofed calls create bookings. |
| [x] | AVS-H003 | P1 | Add real SMS provider adapter. | Production SMS provider implementation behind interface. | Marketing campaigns. | Confirmation/cancel messages can be delivered. | Adapter tests, sandbox smoke. | SMS vendor failures block launch. |
| [x] | AVS-H004 | P1 | Add SMS status webhook. | Persist delivery status callbacks. | Reply parsing. | Message status is visible and idempotent. | Webhook tests. | Failed delivery is invisible. |
| [x] | AVS-H005 | P1 | Add provider webhook idempotency. | Deduplicate voice/SMS provider callbacks. | Generic webhook rewrite. | Retries do not duplicate bookings/messages. | Idempotency tests. | Provider retries cause duplicates. |
| [x] | AVS-H006 | P1 | Add public webhook rate limiting. | Provider/IP-aware limits for product webhooks. | WAF setup. | Abuse is bounded without blocking expected provider traffic. | API tests. | Public endpoints are DoS-prone. |
| [x] | AVS-H007 | P1 | Add pilot provider runbook. | Phone numbers, secrets, webhooks, retries, test calls, incident steps. | Full on-call program. | Operator can configure pilot safely. | Docs review. | Misconfiguration breaks pilot. |

### EPIC I - Call transfer

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-I001 | P1 | Add business transfer settings. | Enable/disable transfer, destination policy, hours. | Staff acceptance flow. | Transfer can be configured per business. | Model/API tests. | Calls transfer when business opted out. |
| [x] | AVS-I002 | P1 | Add staff transfer eligibility. | Staff phone, availability, active status, acceptance requirement. | Complex routing. | Eligible staff list is tenant/business scoped. | Service tests. | Calls route to wrong/unavailable staff. |
| [x] | AVS-I003 | P1 | Transfer call from IVR. | Provider-neutral transfer intent from press 2 branch. | Provider-specific adapter details. | IVR emits transfer intent when allowed. | IVR tests. | Transfer branch dead-ends. |
| [x] | AVS-I004 | P1 | Add unavailable fallback. | Message or return-to-menu when transfer unavailable/declined. | Voicemail transcription. | Caller gets clear fallback. | IVR tests. | Caller hangs up without path forward. |
| [x] | AVS-I005 | P1 | Cover transfer behavior. | Settings, eligibility, IVR branch, fallback tests. | Live call tests. | Transfer logic passes without real provider. | `make validate`. | Transfer behavior regresses. |

### EPIC J - End-to-end demo and production MVP readiness

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-J001 | P0 | Seed demo business data. | Demo business, staff, services, hours, fake providers. | Production fixtures. | Local seed creates deterministic demo scenario. | Seed tests/smoke. | Demo cannot be reproduced. |
| [x] | AVS-J002 | P0 | Smoke manual booking flow. | Create booking through API and verify fake SMS/calendar. | Real provider smoke. | Script proves manual flow works locally. | Smoke command/test. | API path works only in unit tests. |
| [x] | AVS-J003 | P0 | Smoke IVR simulated booking. | Simulated call through booking, fake SMS, fake calendar. | Twilio smoke. | Script proves local call-to-booking path. | Smoke command/test. | Voice flow cannot be demoed. |
| [x] | AVS-J004 | P0 | Smoke cancellation flow. | Cancel booking and verify notification/calendar update. | Customer self-cancel. | Script proves cancellation side effects. | Smoke command/test. | Lifecycle changes diverge. |
| [x] | AVS-J005 | P0 | Document README demo scenario. | Local setup and expected demo outputs. | Marketing landing page. | New developer can run the demo. | Docs review. | Product appears unusable locally. |
| [x] | AVS-J006 | P1 | Add MVP pilot deployment checklist. | Env, secrets, provider config, worker, monitoring, backup, rollback. | Full SRE program. | Pilot operator has checklist before real calls. | Docs review, policy guards. | Pilot launches with missing safeguards. |

### EPIC K - Booking mode and subscription plan

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-K001 | P0 | Add booking_mode and subscription_plan to Business. | Two independent dimensions: booking_mode (operational — internal vs external link) and subscription_plan (commercial — stored only). IVR press-1 dispatches on booking_mode. External mode sends SMS with booking URL. PlanPolicyService stub as future billing seam. | Billing enforcement, plan limits. | Model, migration, schema, API, IVR dispatch, notification, tests all done. | `make validate`, 631 tests pass. | booking_mode conflated with pricing; kept strictly separate. |

### EPIC L - Owner acquisition and manual pilot onboarding

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | AVS-L001 | P1 | Owner lead intake for manual pilot onboarding. | Public lead submission endpoint (`POST /api/v1/owner-leads`). `OwnerLead` model (not tenant-scoped). Admin listing + status management. Rate-limited (5/hour/IP). URL/email/phone validation. Phone normalization. Two booking mode interests: external_booking_link and standalone_booking. | Full owner dashboard, billing, phone provisioning, automated onboarding. | Public endpoint returns 201, stores lead, exposes only public-safe fields. Admin can list/get/update status. 35 tests pass. | `make validate`. 673 tests pass. | Interested salons have no clear path to pilot. |
| [x] | AVS-L002 | P1 | Manual pilot onboarding runbook. | Operator checklist for onboarding a salon from a submitted lead. Covers both external_booking_link and standalone_booking modes. IVR test call verification. Transfer phone config. | Automated onboarding. | Developer/operator can onboard one test salon from lead data. | Docs review / policy guards. | Pilot setup is inconsistent. |
| [x] | AVS-L003 | P2 | Minimal owner dashboard skeleton. | Define pages/routes needed for future owner-facing UI. No full implementation. | Full frontend app. | Docs define dashboard MVP scope clearly. | Docs review. | Frontend work starts without agreed scope. |
| [x] | AVS-L004 | P4 | Self-service onboarding API. | Signup/guided setup flow via API (staff, services, hours). | Frontend wizard, billing. | Owner can complete initial setup by API calls. | API tests. | Manual onboarding blocks scale. |

See `docs/product/owner-acquisition.md` for flow, booking modes, and upgrade path.

## Production expansion backlog

Expansion work starts after the first working product. These tasks should not be
started until the MVP foundation backlog has a green local simulated flow unless
the task explicitly de-risks the MVP.

### PRIORITY 1 - Must have for production pilot

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | P1-001 | P1 | Send reminder SMS. | Reminder schedule before appointment. | Marketing campaigns. | Reminder intent is queued and sent once. | Worker tests. | No-shows remain high. | done: `enqueue_due_reminders()` runs on the worker maintenance tick, queues one BOOKING_REMINDER per confirmed booking within `settings.reminder_lead_minutes`, idempotent via existing-outbox-row check — `tests/test_avs_p1001_reminder_sms.py` |
| [x] | P1-002 | P1 | Handle SMS reply confirm/cancel. | Parse simple replies and update booking. | Free-form NLP. | Confirm/cancel replies are idempotent. | Webhook tests. | Customers cannot manage bookings. | done: `handle_sms_reply()` parses C/CONFIRM/Y/YES and X/CANCEL/N/NO, cancels the customer's soonest upcoming confirmed booking (idempotent — already-cancelled is a no-op), wired to `POST /webhooks/twilio/sms/{business_id}/inbound` — `tests/test_avs_p1002_sms_reply_confirm_cancel.py`, `tests/test_twilio_sms.py` |
| [x] | P1-003 | P1 | Reschedule by customer IVR. | Customer finds booking by phone and selects new slot. | Staff preference. | Reschedule updates booking/SMS/calendar. | IVR E2E tests. | Support burden stays high. | done: main menu option 3 finds the caller's soonest upcoming confirmed booking by caller ID; caller can cancel or reschedule (same service/staff, new slot via cancel+create) — see `docs/specs/ivr-reschedule.md` and `tests/test_avs_p1003_ivr_reschedule.py` |
| [x] | P1-004 | P1 | Reschedule by business/admin. | API workflow for changing slot/staff. | Frontend. | Business can reschedule and notify parties. | API/service tests. | Staff cannot recover schedule changes. | done: `POST /businesses/{business_id}/bookings/{booking_id}/reschedule` (admin-only) calls the shared `reschedule_booking()` (cancel old + create new at the new time, same service/staff) — `tests/test_avs_p1004_admin_reschedule.py` |
| [x] | P1-005 | P1 | Handle IVR timeout/no input. | Timeout prompts and terminal state. | Voicemail. | No-input flow is predictable and audited. | IVR tests. | Calls hang or loop forever. | done: `no_input_count` tracked on `VoiceSession`, explicit re-prompt on silence, session terminates (`EXPIRED`) after 3 consecutive misses — `tests/test_avs_p1005_ivr_no_input.py` |
| [x] | P1-006 | P1 | Handle IVR invalid input. | Retry count and fallback. | Natural language. | Invalid keys do not corrupt session. | IVR tests. | Bad input creates wrong booking. | done: `invalid_key_count` tracked cumulatively across steps, session terminates (`EXPIRED`) after 5 invalid keys — `tests/test_avs_p1006_ivr_invalid_input.py` |
| [x] | P1-007 | P1 | Add repeat menu option. | Key to replay current prompt/options. | Multi-language prompts. | Caller can repeat menu at each step. | IVR tests. | Caller abandons flow. | done: `*` replays the current prompt at every interactive step without advancing state or incrementing `invalid_key_count` — `tests/test_avs_p1007_ivr_repeat_menu.py` |
| [x] | P1-008 | P1 | Add backend-unavailable fallback. | Graceful message/transfer when DB/Redis unavailable. | Full disaster recovery. | IVR does not expose errors or create partial booking. | Failure tests. | Outages produce bad caller experience. | done: voice webhook routes catch `OperationalError`/`RedisError` (and the `HTTPException(503)` `enforce_rate_limit_counter()` already raises for a Redis outage) and return graceful TwiML instead of a raw error; real 403/429 still propagate normally — `tests/test_avs_p1008_ivr_backend_unavailable.py` |
| [x] | P1-009 | P1 | Extract queues for SMS/calendar. | Separate job types/queues or outbox processors. | New queue vendor. | Side effects are independently observable. | Worker tests. | One failing integration blocks another. | done: every job type gets its own Redis list via `queue_name_for_job_type()`; the worker polls each known type's queue in turn (short per-queue timeout) instead of one shared FIFO list, so a backlog in one type can't delay another — `tests/test_worker.py::test_notification_job_is_not_blocked_by_calendar_backlog` |
| [x] | P1-010 | P1 | Add exponential backoff. | Backoff policy for SMS/calendar retries. | Manual retry UI. | Retry intervals are bounded and tested. | Worker tests. | Provider incidents amplify traffic. | covered by AVS-E007: `calculate_retry_delay_seconds()` in `app/core/job_queue.py` uses 2^(attempts-1) with configurable base and max caps |
| [x] | P1-011 | P1 | Add DLQ and alerting. | Failed async operation DLQ plus alert signal. | Pager provider setup. | Exhausted jobs are visible. | Worker/metrics tests. | Silent async data loss. | done: new `worker_failed_queue_depth` Prometheus gauge refreshed every maintenance tick via `get_failed_queue_depth()`, plus `WorkerFailedQueueBacklog`/`WorkerJobFailureRate` Alertmanager rules in `observability/prometheus/rules/worker-alerts.yml` — no Slack/PagerDuty credentials exist in this repo, so the alert signal is Prometheus/Alertmanager (already wired), not a new external webhook integration — `tests/test_job_queue.py`, `tests/test_worker.py`, `tests/test_worker_metrics.py` |
| [x] | P1-012 | P1 | Monitor failed integrations. | Metrics/logs for provider failures and backlog. | Full dashboard. | Alerts can be wired from documented metrics. | Metrics tests/docs. | Pilot failures go unnoticed. | done: `sms_provider_requests_total{provider,status}` and `calendar_provider_requests_total{provider,operation,status}` instrumented at the actual provider call sites (`SmsProvider.send()`, calendar provider's `create_event()`/`cancel_event()`) — finer-grained than job-level since a job can retry against the provider multiple times; documented in `docs/observability-production.md` — `tests/test_notification_worker.py`, `tests/test_calendar_worker.py`, `tests/test_worker_metrics.py` |
| [x] | P1-013 | P1 | Expand booking lifecycle audit logs. | Add audit events for reschedule, SMS reply accept/cancel, and admin override — create/cancel already logged. | Compliance export. | All lifecycle events are queryable with actor. | Service/API tests. | Disputes lack evidence. | done: create/cancel/reschedule/SMS-reply-confirm/admin-override all logged now — `BOOKING_RESCHEDULED` (linked to the old booking id via `source`) added in `reschedule_booking()`, `BOOKING_CONFIRMED` added in the SMS reply CONFIRM path (SMS reply CANCEL already produced `BOOKING_CANCELLED` via the existing `cancel_booking()` path), admin override now logs `BOOKING_OVERRIDE_CREATED`/`BOOKING_OVERRIDE_CANCELLED` (P3-012) — `tests/test_booking_audit.py`, `tests/test_avs_p1002_sms_reply_confirm_cancel.py`, `tests/test_avs_p3012_admin_override.py` |

### PRIORITY 2 - High business impact

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | P2-001 | P2 | Add basic CRM clients table. | Client profile beyond booking customer record. | Marketing automation. | Business can store client basics. | Model/API tests. | Customer history stays fragmented. | done: new `Client` model (name/email/phone/notes), optionally linked 1:1 to a `Customer` via `customer_id` (unique per business); CRUD at `/businesses/{business_id}/clients` (admin-only writes); migration `p2001a2b3c4d5e` — `tests/test_avs_p2001_crm_clients.py` |
| [x] | P2-002 | P2 | Link bookings to clients. | Associate bookings with CRM client. | Merge UI. | Booking history rolls up to client. | Service tests. | Duplicate identity grows. | done: no new column — `Client.customer_id` is already unique per business (P2-001), so `Booking.customer_id` already provides a complete `Booking -> Customer <- Client` path; `get_bookings_for_client()` in `client_service.py` — `tests/test_avs_p2002_client_booking_history.py` |
| [x] | P2-003 | P2 | Recognize returning caller. | Match caller by normalized phone in IVR. | Voice biometrics. | IVR can greet/use known client safely. | IVR tests. | Returning users get slow flow. | done: `start_session()` personalizes the main-menu greeting ("Welcome back, {name}!") when caller_phone matches an existing Customer for the exact business+tenant, preferring the linked Client name if one exists; never crosses business/tenant boundaries (same matching already enforced by `get_customer_by_phone()`/`get_client_by_customer_id()`) — `tests/test_avs_p2003_ivr_returning_caller.py` |
| [x] | P2-004 | P2 | Add client booking history. | Admin/API history view. | Frontend. | Business can inspect client visits. | API tests. | Staff lack context. | done: `GET /businesses/{business_id}/clients/{client_id}/bookings` (paginated `BookingRead` list) exposes `get_bookings_for_client()` from P2-002 over HTTP — `tests/test_avs_p2004_client_booking_history_api.py` |
| [x] | P2-005 | P2 | Add GDPR delete endpoint. | Delete/anonymize customer data per business policy. | Legal policy automation. | Deletion preserves required booking/audit constraints. | Privacy tests. | Privacy requests cannot be handled. | done: `POST /businesses/{business_id}/customers/{customer_id}/gdpr-delete` (admin-only) anonymizes PII on `Customer` (and a linked `Client`, if any) rather than hard-deleting — `Booking.customer_id` has no `ON DELETE` clause, so a customer with booking history can't be removed without breaking that FK or the audit trail; applies regardless of booking status; logs `AuditAction.CUSTOMER_ANONYMIZED` — `tests/test_avs_p2005_gdpr_delete.py` |
| [x] | P2-006 | P2 | Add preferred staff selection. | IVR lets caller pick staff. | Staff recommendation engine. | Availability filters by selected staff. | IVR/availability tests. | Customers cannot choose provider. | done: new `STAFF_SELECTION` IVR step between service and slot selection; offered only when 2+ active staff have a configured (staff-specific) working-hours schedule — `get_available_slots()` matches `staff_id` strictly against that staff member's own hours with no business-level fallback, so an unscheduled staff member would always dead-end in "no slots"; with 0 or 1 such staff the step auto-skips (single staff auto-selected, none falls back to "any available"); caller can also press 0 for "any available staff"; `VoiceSession.selected_staff_id` (pre-existing column) now actually gets set and threaded through `_find_slots()`/`get_available_slots()`/`create_booking()` — `tests/test_avs_p2006_ivr_staff_selection.py` |
| [x] | P2-007 | P2 | Suggest last staff member. | Use booking history to propose previous staff. | Personalization model. | Returning caller can reuse last staff. | IVR tests. | Repeat customer flow is inefficient. | done: new `get_last_staff_booking()` looks up the caller's most recent past booking (matched by phone, same exact business+tenant scoping as the P2-003 returning-caller greeting) with a `staff_id` set; if that staff member is still active and schedulable (P2-006's filter), they're reordered to the front of the staff-selection menu — always option "1" — and called out by name ("press 1 for {name}, who you saw last time"); no history, or a staff member who's no longer active/schedulable, leaves the menu exactly as P2-006 left it — `tests/test_avs_p2007_ivr_suggest_last_staff.py` |
| [x] | P2-008 | P2 | Add multi-service appointment model. | Multiple services in one booking. | Packages/payments. | Booking can represent ordered service list. | Model/service tests. | Larger appointments cannot be booked. | done: new additive `BookingLineItem` model/table (`booking_id`, `service_id`, `position`, `duration_minutes` snapshot) lets a booking carry an ordered list of services; `Booking.service_id`/`ends_at` keep their existing meaning (primary/first service) so every existing single-service code path (IVR, availability search, calendar sync) is completely unaffected; `add_booking_line_item()`/`list_booking_line_items()`/`get_booking_total_duration_minutes()` in `booking_service.py`; migration `p2008a2b3c4d5e`; wiring this into availability/IVR is P2-009 — `tests/test_avs_p2008_multi_service_booking.py` |
| [x] | P2-009 | P2 | Support combined duration availability. | Slot generation for total service duration. | Parallel services. | Availability uses combined duration. | Availability tests. | Multi-service bookings overlap. | done: new `get_available_slots_for_total_duration()` sibling of `get_available_slots()` searches for a combined duration across multiple services (built from P2-008's `BookingLineItem` rows) instead of a single `service_id`'s `duration_minutes`; both share the same private slot-generation core (`_get_available_slots_for_duration()`), parameterized by duration, so the existing single-service function/signature/call sites (IVR, availability API) are completely unchanged; not yet wired into `create_booking()` or the IVR flow itself, which is a later ticket — `tests/test_avs_p2009_combined_duration_availability.py` |
| [x] | P2-010 | P2 | Add waitlist model. | Customer desired time/service/staff window. | Auto-offer flow. | Waitlist entry can be created and managed. | Model/API tests. | No path when fully booked. | done: new `WaitlistEntry` model/table — `customer_id`, `service_id`, optional `staff_id` (preferred staff), `desired_date`, `status` (`WaitlistEntryStatus`: WAITING/OFFERED/CONFIRMED/EXPIRED/CANCELLED on a plain `String` column); `create_waitlist_entry()`/`list_waitlist_entries()`/`update_waitlist_entry_status()` in new `waitlist_service.py`; migration `p2010a2b3c4d5e`; not yet wired into the cancellation flow (P2-011) or offer timeout/escalation (P2-012) — `tests/test_avs_p2010_waitlist_model.py` |
| [x] | P2-011 | P2 | Offer waitlist after cancellation. | Notify eligible waitlist customers. | Bidding/auction. | Cancellation can trigger offer intent. | Worker tests. | Open slots stay unfilled. | done: `cancel_booking()` now calls new `find_matching_waitlist_entries()` (matches business/service/desired_date, plus staff — entries with no staff preference always match, entries wanting a specific staff member only match if that's the staff member whose slot just freed up) and transitions only the oldest matching WAITING entry to OFFERED, recording the freed slot's actual staff on the new `offered_for_staff_id` column (migration `p2012a2b3c4d5e`) and enqueuing a new `WAITLIST_OFFER` SMS notification (new `NotificationPurpose` value, plain `String` column, no DDL change) via `enqueue_waitlist_offer()`; the rest stay WAITING — if the offered customer doesn't respond, P2-012's timeout/escalation offers the next one — `tests/test_avs_p2011_waitlist_offer_on_cancellation.py` |
| [x] | P2-012 | P2 | Add waitlist timeout/escalation. | Expire offers and move to next customer. | Complex prioritization. | Offers cannot block waitlist forever. | Worker tests. | Waitlist stalls. | done: new `expire_stale_waitlist_offers()` in `waitlist_service.py`, called from `run_scheduled_maintenance()` in the worker, finds OFFERED entries whose `updated_at` is older than the new `settings.waitlist_offer_timeout_minutes` (default 60), marks each EXPIRED, then calls `find_matching_waitlist_entries()` (from P2-011) to offer the next-oldest eligible WAITING entry for the same business/service/desired_date instead — matched against the expired entry's `offered_for_staff_id` (the freed slot's actual staff), not its own `staff_id` preference, since a no-preference customer's expired offer can still be for a specific staff member's slot — propagating `offered_for_staff_id` to the new winner so the chain stays correct across repeated escalations; enqueues a new `WAITLIST_OFFER` notification via `enqueue_waitlist_offer()` — together with P2-011 offering only one waiter at a time, a non-responsive customer can't block the waitlist forever — `tests/test_avs_p2012_waitlist_timeout_escalation.py` (incl. end-to-end cancellation-then-timeout-escalation and staff-tracking regressions) |
| [ ] | P2-013 | P2 | Add owner metrics API. | Bookings, missed calls, conversion, failures. | Full BI dashboard. | Metrics endpoint returns tenant-safe aggregates. | API tests. | Owner cannot measure value. |
| [ ] | P2-014 | P2 | Add CSV export. | Export bookings/customers within tenant. | Accounting integration. | Exports are tenant-scoped and bounded. | API/security tests. | Manual reporting remains painful. |

### PRIORITY 3 - Operational extensions

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [x] | P3-001 | P3 | Add salon opening hours. | Business-level hours independent of staff. | Multi-location hours. | Salon hours can be configured. | Model/API tests. | Staff availability ignores business closures. | done: discovered while scoping this task that `POST /businesses/{business_id}/working-hours` hardcoded `staff_id=None` — there was no API path to configure a *staff-specific* schedule at all (only via direct service calls in tests/seed scripts), even though `get_available_slots()` and P2-006's IVR staff-selection menu both depend on staff having their own `WorkingHours` rows; added an optional `staff_id` field to `WorkingHoursCreate`, validated against the business via `require_staff_in_business()` (same pattern as AVS-TD-029/032); the create endpoint's docstring now documents the business-wide-vs-staff-specific distinction and the explicit "no intersection here, that's P3-002" boundary — `tests/test_avs_p3001_salon_hours_api.py` |
| [x] | P3-002 | P3 | Intersect salon/staff hours. | Availability requires both salon and staff open. | Resource rooms. | Slots only appear when both are open. | Availability tests. | Bookings appear outside salon hours. | done: `_get_available_slots_for_duration()` now intersects a staff member's specific `WorkingHours` windows against the business's wide ones via new `_intersect_time_windows()` (full pairwise overlap, handles split shifts on either side) — a slot only counts if both are open, and a staff window wider than the salon's gets clipped, not just unioned; fallback (use the other side's hours when one side has zero `WorkingHours` rows configured at all) is symmetric and based on whether that side has any row on *any* day, not just the queried one — a side with a managed-but-partial schedule (e.g. salon or staff open Mon-Fri only) stays closed on an unconfigured day rather than silently inheriting the other side's hours that day; two asymmetric variants of this bug (staff-side, then salon-side) were each caught in cross-provider review and fixed pre-merge with dedicated regression tests; this also fixed `_schedulable_staff()` in `ivr_service.py` (P2-006), whose docstring explicitly assumed "no fallback" and excluded every such staff member from the IVR menu; the demo seed (3 staff, business-wide hours only) made per-staff IVR selection effectively dead before this fix — required updating `tests/test_avs_j003_smoke_ivr_booking.py`'s scripted press sequence and `tests/test_avs_p2006_ivr_staff_selection.py`'s exclusion test to match; `AvailabilityException`'s existing cross-scope OR/union semantics are unchanged, deliberately deferred to P3-003 — `tests/test_availability.py`, `tests/test_avs_p2009_combined_duration_availability.py` |
| [x] | P3-003 | P3 | Add salon closures/holidays. | Business-wide closed days/exceptions. | Staff-specific PTO. | Closures remove all affected slots. | Availability tests. | Holiday bookings happen. | done: business-wide closure exclusion and overlap validation already worked (pre-existing test, P3-004); added the missing API clarity and precedence/isolation tests the audit flagged — the create endpoint's docstring now documents that a business-wide (`staff_id=null`) closure always wins over any staff-specific exception for the same date, and that a staff-specific exception never leaks into other staff members' or an "any available staff" search; a clarifying comment on `_get_available_slots_for_duration()`'s exception-merging block documents this is deliberately an OR/union (not P3-002's intersection) since an exception means "this date differs from the rule," not "this is the rule" — `tests/test_avs_p3003_salon_closures.py` |
| [x] | P3-004 | P3 | Add staff time blocks. | One-off staff unavailable blocks. | Recurring rules. | Staff blocks remove affected slots. | Availability tests. | Staff personal time gets booked. | done: `AvailabilityException` model already supported one-off blocks and exclusion (unchanged); added the missing validation — `create_availability_exception()` now rejects a `staff_id` that doesn't belong to the business (404, matching the `require_*_in_business()` pattern) and rejects a new exception that conflicts with an existing one for the exact same (business_id, staff_id, date) scope via new `_ensure_no_conflicting_exception()`: a full-day closure can't coexist with any other row for that scope/date, and two "special hours" rows can't have overlapping time windows (non-overlapping windows, e.g. 9-12 and 13-17, remain allowed — that's the existing intentional lunch-block pattern); deliberately does not cross-check a staff-specific row against a business-wide row for the same date, since that precedence question is P3-002/003's job — `tests/test_avs_p3004_staff_blocks.py` |
| [x] | P3-005 | P3 | Add recurring staff blocks. | Lunches/recurring unavailable windows. | Complex recurrence UI. | Recurring blocks apply predictably. | Availability tests. | Daily breaks remain bookable. | done: model decision per `docs/adr/0003-recurring-staff-blocks.md` (Accepted) — new `RecurringStaffBlock` model (`app/models/recurring_staff_block.py`), business-scoped CRUD with same-scope overlap validation (`app/services/recurring_staff_block_service.py`), API at `/businesses/{business_id}/recurring-staff-blocks` (admin-only writes); `_get_available_slots_for_duration()` now applies blocks as a third precedence step that *subtracts* from whatever `WorkingHours`/`AvailabilityException` left in place via new `_subtract_time_windows()`, applied after exceptions so it clips the then-current schedule rather than a frozen snapshot — verified to stay correct after working hours change later, the bug a recurrence rule on `AvailabilityException` would have reintroduced — `tests/test_avs_p3005_recurring_staff_blocks.py`, cross-business isolation tests added to `tests/test_fix_tenant_business_scoping.py` |
| [ ] | P3-006 | P3 | Design deposits/prepayments. | ADR for payment state, booking holds, refunds. | Stripe implementation. | Architecture approved before payment code. | Docs review. | Payments corrupt booking lifecycle. |
| [ ] | P3-007 | P3 | Add Stripe payment links. | Payment-link creation for selected services. | Stripe Billing subscriptions. | Booking can require/link deposit payment. | Adapter tests. | Payment failures cause bad bookings. |
| [ ] | P3-008 | P3 | Add pending-payment booking state. | Hold expiry and transition rules. | Full checkout. | Pending holds expire safely. | Worker/service tests. | Slots remain locked after abandoned payment. |
| [x] | P3-009 | P3 | Add multilingual IVR prompt architecture. | Prompt keys/templates per language. | Translation content. | Flow can choose language without logic fork. | IVR tests. | Localization duplicates IVR code. | done: new `app/core/ivr_prompts.py` — `PromptKey` enum (one entry per distinct prompt/label template), `_PROMPTS: dict[locale, dict[PromptKey, str]]` (only `en` populated, by design — translation content is out of scope), `resolve_prompt(key, *, locale, **kwargs)` (falls back to `IVR_DEFAULT_LOCALE` for an unknown locale or a locale missing a specific key, so a partial translation degrades gracefully), `format_option_list()` (centralizes the repeated "press {key} for {label}" join pattern that was previously duplicated at ~7 call sites in `ivr_service.py`); every hardcoded prompt string and static `IvrOption` label in `ivr_service.py` now resolves through these, gated by a single `_session_locale(session)` helper — adding a real locale later means changing that one function plus adding one `_PROMPTS` entry, zero step-handler changes; exact rendered text preserved byte-for-byte, verified by the full existing IVR test suite (99 tests across `test_ivr_e2e.py`, `test_ivr_service.py`, and every `test_avs_p1*/p2*_ivr_*.py`) passing unchanged — `tests/test_avs_p3009_ivr_prompt_keys.py` (new: key/locale resolution, fallback for unknown locale and partially-translated locale, option-list join, and an explicit "adding a second locale requires zero ivr_service.py changes" proof) |
| [ ] | P3-010 | P3 | Add private staff calendar visibility rules. | Avoid exposing private calendar details. | Calendar UI. | Sync stores busy/free only where needed. | Privacy tests. | Sensitive staff details leak. |
| [ ] | P3-011 | P3 | Add calendar conflict import spike. | Investigate one-way busy import. | Full two-way sync. | ADR documents safe approach. | Docs review. | External conflicts missed. |
| [x] | P3-012 | P3 | Add manual admin override workflow. | Override booking/cancel with a mandatory reason and a distinct audit trail (does not bypass the DB-level no-overlap safety constraint for a genuine same-staff conflict — see evidence). | Frontend UI; force-overbooking a specific staff member's slot past the no-overlap constraint (would require a migration weakening that Critical-priority safety constraint — out of scope, see evidence). | Overrides are explicit and audited. | API tests. | Support cannot resolve edge cases. | done: `POST /businesses/{business_id}/bookings/override` and `POST /businesses/{business_id}/bookings/{booking_id}/override-cancel`, both admin-only (`require_role("admin")`) with a required, non-blank `reason`; both call the existing `create_booking()`/`cancel_booking()` with a new `override=True` flag, logging the new `AuditAction.BOOKING_OVERRIDE_CREATED`/`BOOKING_OVERRIDE_CANCELLED` (with `source` set to the admin's reason, queryable separately from regular `BOOKING_CREATED`/`BOOKING_CANCELLED`) instead of changing booking mechanics — override-create does **not** bypass the DB-level `no_overlapping_staff_bookings` exclusion constraint for a genuine same-staff conflict (still 409s), a deliberate scope decision recorded in `tests/test_avs_p3012_admin_override.py`'s module docstring; unblocks P1-013's remaining admin-override audit gap — `tests/test_avs_p3012_admin_override.py` |
| [x] | P3-013 | P3 | Add integration reconciliation job. | Detect stale SMS/calendar outbox records. | Provider-specific repair UI. | Stale records are reported/retried. | Worker tests. | Integration drift accumulates. | done: new `app/services/reconciliation_service.py` (`reconcile_stale_notifications()`, `reconcile_stale_calendar_events()`), wired into the existing `run_scheduled_maintenance()` tick. Closes the gap where the DB commit (outbox/calendar row) and the Redis job enqueue are two separate steps — a crash or transient Redis failure between them left a `PENDING` row with no job ever processing it. Gated on `COALESCE(reconciled_at, created_at)` (new nullable column on both models, migration `p3013a2b3c4d5e`) rather than `created_at` alone — caught by cross-provider review, which flagged a `created_at`-only sweep as re-enqueuing the same stale row on every maintenance tick forever, risking a duplicate SMS/calendar-event send if the original job was still in flight. New `integration_reconciliation_requeued_total{record_type}` metric surfaces ongoing drift, per the roadmap's explicit "Provider-specific repair UI" exclusion — `tests/test_reconciliation_service.py`, extended `tests/test_worker.py`/`tests/test_worker_metrics.py` |
| [ ] | P3-014 | P3 | Write two-way calendar sync ADR. | Risks, source of truth, conflict policy. | Implementation. | ADR rejects or scopes two-way sync safely. | Docs review. | Calendar becomes competing source of truth. |

### PRIORITY 4 - SaaS model and scale

| Status | ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|--------|----|----------|------|-------|-----|------------|------------|------|
| [ ] | P4-001 | P4 | Audit product multi-tenancy queries. | Review every product query for tenant filters. | Foundation audit. | Query audit checklist is complete. | Security review/tests. | Cross-tenant data leakage. | partial: `tests/test_product_tenant_isolation.py` covers initial product scope; systematic query-by-query checklist and CI guard not yet created |
| [ ] | P4-002 | P4 | Add product tenant guards. | Middleware/dependencies/helpers for product APIs. | RLS migration. | Product APIs consistently require tenant context. | API/security tests. | Missing guard exposes data. | partial: `require_business()` and per-service `tenant_id` filter pattern in place; standardized dependency-injected tenant guard not yet abstracted |
| [ ] | P4-003 | P4 | Add cross-tenant leakage tests. | All product APIs tested for denial. | Manual review only. | Every product route has isolation coverage. | `make validate`. | Isolation regressions merge. | partial: `tests/test_product_tenant_isolation.py` and per-feature isolation tests exist; per-route coverage requirement and enforcement in CI not yet added |
| [ ] | P4-004 | P4 | Add self-service salon onboarding. | Signup/setup business profile. | Billing. | New salon can start setup safely. | API tests. | Manual onboarding limits scale. | partial: AVS-L004's `POST /api/v1/onboarding` already covers "setup business profile" (creates business+staff+services+hours atomically); the "signup" half — a new salon owner provisioning their own tenant/admin account without a manually-created one — is not implemented (tenant/user creation is still manual, see `docs/runbooks/pilot-onboarding.md`) |
| [x] | P4-005 | P4 | Add onboarding wizard API. | Staff/service/hours guided setup endpoints. | Frontend. | Setup flow can be completed by API. | API tests. | Configuration remains error-prone. | done — duplicate/already covered by AVS-L004's `POST /api/v1/onboarding` (`app/api/routes/onboarding.py`, `app/services/onboarding_service.py`), which already provides exactly this: staff/service/hours guided setup in one API call. Found during `docs/audits/p3-remaining-backlog-audit.md`; this row was never reconciled against EPIC L when AVS-L004 shipped |
| [ ] | P4-006 | P4 | Add phone provisioning workflow. | Reserve/assign provider numbers. | BYO phone porting. | Number lifecycle is tracked. | Adapter tests. | Phone setup remains manual/unreliable. |
| [ ] | P4-007 | P4 | Add Stripe Billing model. | Subscription/customer/price linkage. | Deposit payments. | Salon subscription state is stored. | Model/webhook tests. | SaaS cannot monetize. |
| [ ] | P4-008 | P4 | Add plans and limits. | Feature limits by plan. | Entitlement UI. | Limits are enforceable in service layer. | Service tests. | Overuse or surprise blocking. |
| [ ] | P4-009 | P4 | Add billing webhooks. | Idempotent Stripe subscription events. | Checkout frontend. | Subscription state updates from webhooks. | Webhook tests. | Billing state drifts. |
| [ ] | P4-010 | P4 | Block after plan limit exceeded. | Enforce booking/staff/service/feature limits. | Sales override UI. | Exceeded plans fail with clear errors. | API tests. | Revenue leakage or bad UX. |
| [ ] | P4-011 | P4 | Add backward compatibility checklist. | Migration/versioning policy for existing salons. | Full API versioning rewrite. | Changes include compatibility review. | Docs/policy review. | Existing salons break on release. |

## Production expansion audit notes

**Audit history:** initial backlog-reality-check audit 2026-06-17 (now
superseded by the table above, which reflects actual current status, not a
point-in-time snapshot). Pre-P3 security/tenancy audit 2026-06-19/22 —
`docs/audits/pre-p3-readiness-audit.md`. Remaining-backlog and
documentation-accuracy audit 2026-06-22 —
`docs/audits/p3-remaining-backlog-audit.md` (current source of truth for
"what's left"; do not rely on the per-item summary previously inlined here,
which described a 2026-06-17 snapshot that predates all of P1, most of P2,
and all of P3).

**Current summary (see `docs/audits/p3-remaining-backlog-audit.md` for full
verification):** 52 P1–P4 items tracked — 33 fully implemented or covered
(all of P1, all of P2 except P2-013/014, 7 of 14 P3 items, and P4-005 via
duplicate coverage by AVS-L004), 4 partially implemented (P4-001/002/003 —
tenancy-audit related — and P4-004, partially covered by the same AVS-L004
endpoint), 15 not started (P2-013/014; P3-006/007/008/010/011/013/014;
P4-006 through P4-011).

**Duplicate found:** P4-005 was accidentally already covered by AVS-L004's
self-service onboarding API, shipped during EPIC L and never reconciled
against the P4 backlog — see the P4-005 row above and
`docs/audits/p3-remaining-backlog-audit.md` §4. No other P1–P4 item was
found to be a side-effect duplicate of MVP or other backlog work.
`PlanPolicyService` is an intentional stub for P4-008 only.

**Recommended order for remaining work** (per
`docs/audits/p3-remaining-backlog-audit.md` §6, continuing the
`pre-p3-readiness-audit.md` §10 execution order):
1. ~~`feat/p3-013-reconciliation-job`~~ — **done** (P3-013 row above).
2. `docs/adr-deposits-architecture` (P3-006) — ADR only, unblocks P3-007/008.
3. `docs/adr-calendar-import-spike` (P3-011) — ADR/spike only.
4. `docs/adr-two-way-calendar-sync` (P3-014) — depends on #3.
5. `feat/p3-010-calendar-visibility` — depends on #3.
6. `feat/p3-007-stripe-payment-links` — depends on #2.
7. `feat/p3-008-pending-payment-state` — depends on #6.
8. P2-013/014 and P4-001 through P4-011 remain sequenced after the P3
   operational-extensions tier per this file's own tier ordering (P4-005 is
   already done — see that row above).

**Next up:** `docs/adr-deposits-architecture` (P3-006).

## Validation commands

Use existing repository validation:

```bash
make validate-ai-workflows
make policy-guards
make validate
```

For documentation-only changes, run `make validate-ai-workflows` and
`make policy-guards`. Run `make validate` when changing runtime code, tests,
dependencies, migrations, or verified runtime claims.

## Product risk register

- **Correctness:** PostgreSQL constraints and transactions must prevent
  appointment double booking.
- **Tenancy:** all product models, queries, jobs, and webhooks must be tenant
  scoped.
- **Privacy:** phone numbers and customer identifiers must be masked in logs.
- **Timezones:** every business must have an explicit timezone and DST tests.
- **Async side effects:** SMS/calendar delivery must be outbox-backed and
  retryable.
- **Provider retries:** voice/SMS/calendar callbacks must be idempotent.
- **Operational readiness:** pilot launch requires smoke tests, metrics, DLQ
  visibility, and runbooks.
