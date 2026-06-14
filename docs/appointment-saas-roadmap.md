# Appointment Voice SaaS Roadmap

This is the product roadmap for turning the current FastAPI backend foundation
into a working **Appointment Voice SaaS** product. It separates verified
foundation capabilities from planned product runtime work.

## Current repository reality

The repository currently contains a production-oriented FastAPI foundation plus
product bootstrap documentation. Verified foundation capabilities include
FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, worker patterns,
webhook/idempotency patterns, observability, Docker, CI, tests, and AI workflow
rules.

The Appointment Voice SaaS product runtime is not implemented yet. There are no
product-specific business/salon, staff, service, availability, booking, voice
session, SMS, calendar, call transfer, billing, or frontend runtime features in
the codebase today.

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

Recommended MVP execution order:

1. `AVS-A002` - Product architecture ADR.
2. `AVS-A003` - Demo flow definition.
3. `AVS-B001` to `AVS-B009` - Core SaaS domain and tenant isolation.
4. `AVS-C001` to `AVS-C006` - Availability engine.
5. `AVS-D001` to `AVS-D007` - Booking engine and double-booking protection.
6. `AVS-E001` to `AVS-E008` - Notification outbox and fake SMS.
7. `AVS-F001` to `AVS-F007` - Calendar adapter and fake provider.
8. `AVS-G001` to `AVS-G010` - IVR simulation.
9. `AVS-J001` to `AVS-J006` - Demo and MVP readiness.
10. `AVS-H001` onward - Real provider pilot integrations.

### EPIC A - Product foundation from template

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-A000 | P0 | Clean up bootstrap status. | Align roadmap, status, README, and debt docs. | Runtime code. | Docs clearly separate foundation from planned product runtime. | `make validate-ai-workflows`, `make policy-guards`. | False readiness claims mislead implementation. |
| AVS-A001 | P0 | Align product fork naming/status. | Review README/status wording for Appointment Voice SaaS transition. | Renaming packages or env defaults. | Readers know this is a foundation transitioning to product. | Docs review, policy guards. | Operators confuse template features with product features. |
| AVS-A002 | P0 | Record core architecture decision. | ADR for PostgreSQL source of truth, adapters, queue/outbox, idempotency, tenancy. | Implementing models/adapters. | ADR accepted before domain implementation starts. | Docs review, policy guards. | Later integrations bypass core booking invariants. |
| AVS-A003 | P0 | Define MVP demo flow. | Document local simulated call-to-booking-to-notification-to-calendar scenario. | Real Twilio/SMS/calendar. | Demo script steps and expected records are described. | Docs review, later smoke test. | Team builds tasks without a shared product target. |

### EPIC B - Core SaaS domain

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-B001 | P0 | Add Business model. | Tenant-scoped business/salon identity, timezone, phone metadata. | Staff/service logic. | Model, schema, service, CRUD/API path, tests. | `make validate`, migration checks. | Missing tenant/timezone basis breaks all scheduling. |
| AVS-B002 | P0 | Add Staff model. | Tenant/business-scoped staff with active status and contact fields. | Transfer logic. | Staff can be created/read/updated/deactivated per business. | `make validate`. | Staff data leaks or stale staff remain bookable. |
| AVS-B003 | P0 | Add Service model. | Business-scoped services with duration, active status, optional price metadata. | Multi-service bookings. | Active services can drive slot duration. | `make validate`. | Bad durations create impossible availability. |
| AVS-B004 | P0 | Add WorkingHours model. | Recurring local day/time windows for staff/business. | Holiday exceptions. | Working hours validate time ranges and timezone assumptions. | `make validate`. | Availability generated from invalid schedules. |
| AVS-B005 | P0 | Add AvailabilityException model. | One-off closed/open windows for staff/business. | Recurring blocks. | Exceptions can override normal working hours. | `make validate`. | Closures or blocks are ignored. |
| AVS-B006 | P0 | Add Customer model. | Business-scoped customer with normalized phone and optional name. | CRM history UI. | Customers dedupe by phone within business. | `make validate`. | Duplicate customers and privacy errors. |
| AVS-B007 | P0 | Add Booking model. | Business/customer/service/staff/time/status/source fields. | Calendar/SMS delivery. | Booking stores start/end/status and lifecycle metadata. | `make validate`. | Booking records cannot support lifecycle/audit. |
| AVS-B008 | P0 | Add domain migrations/indexes. | Alembic revisions, FKs, tenant indexes, uniqueness and conflict indexes. | Destructive migration. | Migrations upgrade/downgrade cleanly; indexes cover core queries. | `make validate`, migration tests. | Slow or unsafe booking queries. |
| AVS-B009 | P0 | Add tenant isolation tests. | Cross-tenant denial/list/read/write tests for product tables. | Full product API coverage. | Product data cannot be accessed across tenants. | `make validate`. | Cross-tenant data leakage. |

### EPIC C - Availability engine

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-C001 | P0 | Generate slots from working hours. | Slot generation from service duration and staff schedule. | Existing booking exclusion. | Slots align to local business schedule. | Unit tests, `make validate`. | Customers see impossible slots. |
| AVS-C002 | P0 | Exclude existing bookings. | Remove slots overlapping active bookings. | DB-level conflict enforcement. | Availability excludes booked staff/time ranges. | Unit/integration tests. | Double-booking shown as available. |
| AVS-C003 | P0 | Exclude exceptions. | Apply closures, blocks, and special hours. | Recurring staff blocks. | Exceptions override normal slot generation. | Unit/integration tests. | Closed times remain bookable. |
| AVS-C004 | P0 | Support business timezone. | Explicit timezone input/output and DST edge cases. | Multi-timezone staff. | Availability is correct across DST transitions. | Timezone tests, `make validate`. | Off-by-one-hour bookings. |
| AVS-C005 | P0 | Add Availability API. | Tenant-scoped endpoint for service/staff/date availability. | Booking creation. | API returns bookable slots with stable contract. | API tests, `make validate`. | Clients depend on unstable availability contract. |
| AVS-C006 | P0 | Cover availability behavior. | Unit and integration tests for C001-C005. | Load testing. | Empty, full, exception, timezone, and tenant cases pass. | `make validate`. | Edge cases regress silently. |

### EPIC D - Booking engine

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-D001 | P0 | Add booking creation service. | Validate business, staff, service, customer, slot, and status. | SMS/calendar side effects. | Service creates valid booking in one transaction. | Unit/integration tests. | Invalid bookings enter source of truth. |
| AVS-D002 | P0 | Prevent double booking in DB. | Constraints/transaction strategy for overlapping staff bookings. | Calendar conflict source of truth. | Concurrent creates cannot double-book same staff/slot. | Concurrency tests, `make validate`. | Revenue-impacting duplicate bookings. |
| AVS-D003 | P0 | Add booking creation API. | Tenant/admin or system endpoint for creating bookings. | IVR endpoint. | API returns booking or conflict error envelope. | API tests. | Clients cannot create bookings consistently. |
| AVS-D004 | P0 | Add booking list/read API. | Tenant-scoped listing, filtering, and single read. | Dashboard metrics. | Business can inspect bookings. | API tests. | Staff cannot verify schedule. |
| AVS-D005 | P0 | Add business cancellation. | Cancel booking with reason and lifecycle state. | Customer self-cancel. | Cancelled booking no longer blocks active availability if policy allows. | API/service tests. | Cancelled slots remain stuck or audit is missing. |
| AVS-D006 | P1 | Add booking audit logs. | Audit lifecycle changes and actor/source. | Full compliance export. | Create/cancel state changes are auditable. | Tests, existing audit patterns. | Disputes cannot be investigated. |
| AVS-D007 | P0 | Add conflict/concurrency tests. | Race tests for same staff/time and cancellation behavior. | Load benchmark. | Tests prove DB-level double-booking protection. | `make validate`. | Python-only checks fail under concurrency. |

### EPIC E - Notification outbox and fake SMS

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-E001 | P0 | Add notification outbox model. | Persist SMS intent, recipient, template/purpose, status, attempts. | Real SMS provider. | Intent is stored before delivery attempt. | Migration/tests. | Lost confirmations on worker/provider failure. |
| AVS-E002 | P0 | Add SMS provider interface. | Provider-neutral send contract and result mapping. | Twilio implementation. | Code can send through fake or real adapter later. | Unit tests. | Business logic couples to one vendor. |
| AVS-E003 | P0 | Add fake SMS provider. | Local/dev/test provider that records messages. | Real delivery. | Tests can assert sent/intended messages without network. | Unit/integration tests. | Local demos require paid provider. |
| AVS-E004 | P0 | Enqueue booking confirmation SMS. | Customer and business confirmation intents after booking. | Reminder SMS. | Booking create enqueues expected intents idempotently. | Service tests. | Bookings happen without notification. |
| AVS-E005 | P0 | Enqueue cancellation SMS. | Customer and business cancellation/change intent. | Reschedule messages. | Cancellation enqueues expected intents. | Service tests. | Cancelled appointments are not communicated. |
| AVS-E006 | P0 | Add notification worker. | Use existing worker pattern to process outbox/send jobs. | Separate queue system. | Worker transitions pending/sent/failed statuses. | Worker tests. | Side effects block API or disappear. |
| AVS-E007 | P1 | Add retry/backoff/DLQ. | Retry failed sends and route exhausted attempts to DLQ. | Provider status webhooks. | Failed notifications are recoverable/visible. | Worker tests. | Silent notification loss. |
| AVS-E008 | P0 | Cover notification behavior. | Outbox, fake provider, enqueue, worker tests. | Provider certification. | Happy path and failure path pass. | `make validate`. | Async notification path regresses. |

### EPIC F - Calendar adapter foundation

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-F001 | P0 | Add calendar provider interface. | Provider-neutral create/update/cancel contract. | Google OAuth. | Booking code depends on interface only. | Unit tests. | Calendar provider dictates domain design. |
| AVS-F002 | P0 | Add calendar integration model. | Business/staff calendar settings and fake provider config. | Real OAuth tokens. | Business can have configured calendar integration state. | Migration/tests. | Sync runs without known destination. |
| AVS-F003 | P0 | Add calendar event table. | Map booking to provider event/status/errors. | Two-way sync. | Calendar event record tracks sync lifecycle. | Migration/tests. | Duplicate or orphaned calendar events. |
| AVS-F004 | P0 | Add fake calendar provider. | Local/dev/test provider storing fake events. | Real Google Calendar. | Demo and tests can verify sync without network. | Unit/integration tests. | Calendar path cannot be tested locally. |
| AVS-F005 | P0 | Create calendar event after booking. | Enqueue/create fake calendar event from booking. | External calendar as source of truth. | Booking produces event intent/result. | Worker/service tests. | Business calendar misses bookings. |
| AVS-F006 | P1 | Cancel/update calendar event. | Reflect cancellation/reschedule in calendar adapter. | Two-way external updates. | Cancellation updates fake calendar event state. | Worker/service tests. | Calendar diverges after lifecycle changes. |
| AVS-F007 | P1 | Cover calendar retry/DLQ. | Retry/backoff/DLQ tests for sync failures. | Real provider status polling. | Failed sync is visible and retryable. | Worker tests. | Calendar failures remain silent. |

### EPIC G - Voice/IVR simulation before real provider

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-G001 | P0 | Add VoiceSession model. | Session state, caller phone, selections, expiry, linked booking. | Real Twilio call SID handling. | Session can persist simulated IVR progress. | Migration/tests. | IVR state is lost or duplicated. |
| AVS-G002 | P0 | Add IVR response abstraction. | Provider-neutral prompts, keypad options, redirect/end/transfer intents. | TwiML adapter. | Simulation and future providers share flow contract. | Unit tests. | Voice flow locks into one provider. |
| AVS-G003 | P0 | Add incoming call simulation harness. | Local endpoint/test helper to start a voice session. | Public webhook. | Developer can simulate inbound call locally. | API/test harness tests. | No local E2E path. |
| AVS-G004 | P0 | Add main menu. | Book appointment or transfer to staff option. | Real transfer. | Press 1 books; press 2 follows transfer branch placeholder. | IVR tests. | Callers cannot reach intended workflow. |
| AVS-G005 | P0 | Add service keypad selection. | Map keypad input to active services. | Speech recognition. | Caller can select configured service. | IVR tests. | Wrong service booked. |
| AVS-G006 | P0 | Add slot proposal keypad flow. | Present available slots and accept keypad choice. | Arbitrary date search. | Caller can select a generated slot. | IVR tests. | Caller cannot complete booking. |
| AVS-G007 | P0 | Confirm booking from IVR. | Create booking from selected service/slot/customer. | SMS/calendar provider delivery. | Simulated IVR creates booking through booking service. | E2E IVR test. | IVR bypasses booking correctness. |
| AVS-G008 | P0 | Handle no available slots. | Prompt/end/fallback path when no slots exist. | Waitlist. | No-slot case is clear and does not create booking. | IVR tests. | Bad user experience or invalid booking. |
| AVS-G009 | P1 | Add voice session expiration. | Expire incomplete sessions and release pending state. | Long-term analytics. | Old sessions cannot complete stale booking. | Worker/service tests. | Stale sessions create wrong bookings. |
| AVS-G010 | P0 | Add E2E IVR simulation test. | Full simulated call, service, slot, booking, fake SMS, fake calendar. | Real provider smoke. | One test demonstrates local product flow. | `make validate`. | MVP cannot be verified end to end. |

### EPIC H - Real provider integrations for pilot

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-H001 | P1 | Add Twilio voice webhook adapter. | Convert Twilio requests/responses to provider-neutral IVR contract. | AI voice. | Twilio can drive existing IVR flow. | Adapter/API tests. | Provider details leak into domain logic. |
| AVS-H002 | P1 | Validate voice webhook signatures. | Verify Twilio signatures and reject invalid requests. | IP allowlisting only. | Invalid signatures fail consistently. | Security tests. | Spoofed calls create bookings. |
| AVS-H003 | P1 | Add real SMS provider adapter. | Production SMS provider implementation behind interface. | Marketing campaigns. | Confirmation/cancel messages can be delivered. | Adapter tests, sandbox smoke. | SMS vendor failures block launch. |
| AVS-H004 | P1 | Add SMS status webhook. | Persist delivery status callbacks. | Reply parsing. | Message status is visible and idempotent. | Webhook tests. | Failed delivery is invisible. |
| AVS-H005 | P1 | Add provider webhook idempotency. | Deduplicate voice/SMS provider callbacks. | Generic webhook rewrite. | Retries do not duplicate bookings/messages. | Idempotency tests. | Provider retries cause duplicates. |
| AVS-H006 | P1 | Add public webhook rate limiting. | Provider/IP-aware limits for product webhooks. | WAF setup. | Abuse is bounded without blocking expected provider traffic. | API tests. | Public endpoints are DoS-prone. |
| AVS-H007 | P1 | Add pilot provider runbook. | Phone numbers, secrets, webhooks, retries, test calls, incident steps. | Full on-call program. | Operator can configure pilot safely. | Docs review. | Misconfiguration breaks pilot. |

### EPIC I - Call transfer

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-I001 | P1 | Add business transfer settings. | Enable/disable transfer, destination policy, hours. | Staff acceptance flow. | Transfer can be configured per business. | Model/API tests. | Calls transfer when business opted out. |
| AVS-I002 | P1 | Add staff transfer eligibility. | Staff phone, availability, active status, acceptance requirement. | Complex routing. | Eligible staff list is tenant/business scoped. | Service tests. | Calls route to wrong/unavailable staff. |
| AVS-I003 | P1 | Transfer call from IVR. | Provider-neutral transfer intent from press 2 branch. | Provider-specific adapter details. | IVR emits transfer intent when allowed. | IVR tests. | Transfer branch dead-ends. |
| AVS-I004 | P1 | Add unavailable fallback. | Message or return-to-menu when transfer unavailable/declined. | Voicemail transcription. | Caller gets clear fallback. | IVR tests. | Caller hangs up without path forward. |
| AVS-I005 | P1 | Cover transfer behavior. | Settings, eligibility, IVR branch, fallback tests. | Live call tests. | Transfer logic passes without real provider. | `make validate`. | Transfer behavior regresses. |

### EPIC J - End-to-end demo and production MVP readiness

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| AVS-J001 | P0 | Seed demo business data. | Demo business, staff, services, hours, fake providers. | Production fixtures. | Local seed creates deterministic demo scenario. | Seed tests/smoke. | Demo cannot be reproduced. |
| AVS-J002 | P0 | Smoke manual booking flow. | Create booking through API and verify fake SMS/calendar. | Real provider smoke. | Script proves manual flow works locally. | Smoke command/test. | API path works only in unit tests. |
| AVS-J003 | P0 | Smoke IVR simulated booking. | Simulated call through booking, fake SMS, fake calendar. | Twilio smoke. | Script proves local call-to-booking path. | Smoke command/test. | Voice flow cannot be demoed. |
| AVS-J004 | P0 | Smoke cancellation flow. | Cancel booking and verify notification/calendar update. | Customer self-cancel. | Script proves cancellation side effects. | Smoke command/test. | Lifecycle changes diverge. |
| AVS-J005 | P0 | Document README demo scenario. | Local setup and expected demo outputs. | Marketing landing page. | New developer can run the demo. | Docs review. | Product appears unusable locally. |
| AVS-J006 | P1 | Add MVP pilot deployment checklist. | Env, secrets, provider config, worker, monitoring, backup, rollback. | Full SRE program. | Pilot operator has checklist before real calls. | Docs review, policy guards. | Pilot launches with missing safeguards. |

## Production expansion backlog

Expansion work starts after the first working product. These tasks should not be
started until the MVP foundation backlog has a green local simulated flow unless
the task explicitly de-risks the MVP.

### PRIORITY 1 - Must have for production pilot

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| P1-001 | P1 | Send reminder SMS. | Reminder schedule before appointment. | Marketing campaigns. | Reminder intent is queued and sent once. | Worker tests. | No-shows remain high. |
| P1-002 | P1 | Handle SMS reply confirm/cancel. | Parse simple replies and update booking. | Free-form NLP. | Confirm/cancel replies are idempotent. | Webhook tests. | Customers cannot manage bookings. |
| P1-003 | P1 | Reschedule by customer IVR. | Customer finds booking by phone and selects new slot. | Staff preference. | Reschedule updates booking/SMS/calendar. | IVR E2E tests. | Support burden stays high. |
| P1-004 | P1 | Reschedule by business/admin. | API workflow for changing slot/staff. | Frontend. | Business can reschedule and notify parties. | API/service tests. | Staff cannot recover schedule changes. |
| P1-005 | P1 | Handle IVR timeout/no input. | Timeout prompts and terminal state. | Voicemail. | No-input flow is predictable and audited. | IVR tests. | Calls hang or loop forever. |
| P1-006 | P1 | Handle IVR invalid input. | Retry count and fallback. | Natural language. | Invalid keys do not corrupt session. | IVR tests. | Bad input creates wrong booking. |
| P1-007 | P1 | Add repeat menu option. | Key to replay current prompt/options. | Multi-language prompts. | Caller can repeat menu at each step. | IVR tests. | Caller abandons flow. |
| P1-008 | P1 | Add backend-unavailable fallback. | Graceful message/transfer when DB/Redis unavailable. | Full disaster recovery. | IVR does not expose errors or create partial booking. | Failure tests. | Outages produce bad caller experience. |
| P1-009 | P1 | Extract queues for SMS/calendar. | Separate job types/queues or outbox processors. | New queue vendor. | Side effects are independently observable. | Worker tests. | One failing integration blocks another. |
| P1-010 | P1 | Add exponential backoff. | Backoff policy for SMS/calendar retries. | Manual retry UI. | Retry intervals are bounded and tested. | Worker tests. | Provider incidents amplify traffic. |
| P1-011 | P1 | Add DLQ and alerting. | Failed async operation DLQ plus alert signal. | Pager provider setup. | Exhausted jobs are visible. | Worker/metrics tests. | Silent async data loss. |
| P1-012 | P1 | Monitor failed integrations. | Metrics/logs for provider failures and backlog. | Full dashboard. | Alerts can be wired from documented metrics. | Metrics tests/docs. | Pilot failures go unnoticed. |
| P1-013 | P1 | Expand booking lifecycle audit logs. | Audit create/cancel/reschedule/source/actor. | Compliance export. | Lifecycle history is queryable. | Service/API tests. | Disputes lack evidence. |

### PRIORITY 2 - High business impact

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| P2-001 | P2 | Add basic CRM clients table. | Client profile beyond booking customer record. | Marketing automation. | Business can store client basics. | Model/API tests. | Customer history stays fragmented. |
| P2-002 | P2 | Link bookings to clients. | Associate bookings with CRM client. | Merge UI. | Booking history rolls up to client. | Service tests. | Duplicate identity grows. |
| P2-003 | P2 | Recognize returning caller. | Match caller by normalized phone in IVR. | Voice biometrics. | IVR can greet/use known client safely. | IVR tests. | Returning users get slow flow. |
| P2-004 | P2 | Add client booking history. | Admin/API history view. | Frontend. | Business can inspect client visits. | API tests. | Staff lack context. |
| P2-005 | P2 | Add GDPR delete endpoint. | Delete/anonymize customer data per business policy. | Legal policy automation. | Deletion preserves required booking/audit constraints. | Privacy tests. | Privacy requests cannot be handled. |
| P2-006 | P2 | Add preferred staff selection. | IVR lets caller pick staff. | Staff recommendation engine. | Availability filters by selected staff. | IVR/availability tests. | Customers cannot choose provider. |
| P2-007 | P2 | Suggest last staff member. | Use booking history to propose previous staff. | Personalization model. | Returning caller can reuse last staff. | IVR tests. | Repeat customer flow is inefficient. |
| P2-008 | P2 | Add multi-service appointment model. | Multiple services in one booking. | Packages/payments. | Booking can represent ordered service list. | Model/service tests. | Larger appointments cannot be booked. |
| P2-009 | P2 | Support combined duration availability. | Slot generation for total service duration. | Parallel services. | Availability uses combined duration. | Availability tests. | Multi-service bookings overlap. |
| P2-010 | P2 | Add waitlist model. | Customer desired time/service/staff window. | Auto-offer flow. | Waitlist entry can be created and managed. | Model/API tests. | No path when fully booked. |
| P2-011 | P2 | Offer waitlist after cancellation. | Notify eligible waitlist customers. | Bidding/auction. | Cancellation can trigger offer intent. | Worker tests. | Open slots stay unfilled. |
| P2-012 | P2 | Add waitlist timeout/escalation. | Expire offers and move to next customer. | Complex prioritization. | Offers cannot block waitlist forever. | Worker tests. | Waitlist stalls. |
| P2-013 | P2 | Add owner metrics API. | Bookings, missed calls, conversion, failures. | Full BI dashboard. | Metrics endpoint returns tenant-safe aggregates. | API tests. | Owner cannot measure value. |
| P2-014 | P2 | Add CSV export. | Export bookings/customers within tenant. | Accounting integration. | Exports are tenant-scoped and bounded. | API/security tests. | Manual reporting remains painful. |

### PRIORITY 3 - Operational extensions

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| P3-001 | P3 | Add salon opening hours. | Business-level hours independent of staff. | Multi-location hours. | Salon hours can be configured. | Model/API tests. | Staff availability ignores business closures. |
| P3-002 | P3 | Intersect salon/staff hours. | Availability requires both salon and staff open. | Resource rooms. | Slots only appear when both are open. | Availability tests. | Bookings appear outside salon hours. |
| P3-003 | P3 | Add salon closures/holidays. | Business-wide closed days/exceptions. | Staff-specific PTO. | Closures remove all affected slots. | Availability tests. | Holiday bookings happen. |
| P3-004 | P3 | Add staff time blocks. | One-off staff unavailable blocks. | Recurring rules. | Staff blocks remove affected slots. | Availability tests. | Staff personal time gets booked. |
| P3-005 | P3 | Add recurring staff blocks. | Lunches/recurring unavailable windows. | Complex recurrence UI. | Recurring blocks apply predictably. | Availability tests. | Daily breaks remain bookable. |
| P3-006 | P3 | Design deposits/prepayments. | ADR for payment state, booking holds, refunds. | Stripe implementation. | Architecture approved before payment code. | Docs review. | Payments corrupt booking lifecycle. |
| P3-007 | P3 | Add Stripe payment links. | Payment-link creation for selected services. | Stripe Billing subscriptions. | Booking can require/link deposit payment. | Adapter tests. | Payment failures cause bad bookings. |
| P3-008 | P3 | Add pending-payment booking state. | Hold expiry and transition rules. | Full checkout. | Pending holds expire safely. | Worker/service tests. | Slots remain locked after abandoned payment. |
| P3-009 | P3 | Add multilingual IVR prompt architecture. | Prompt keys/templates per language. | Translation content. | Flow can choose language without logic fork. | IVR tests. | Localization duplicates IVR code. |
| P3-010 | P3 | Add private staff calendar visibility rules. | Avoid exposing private calendar details. | Calendar UI. | Sync stores busy/free only where needed. | Privacy tests. | Sensitive staff details leak. |
| P3-011 | P3 | Add calendar conflict import spike. | Investigate one-way busy import. | Full two-way sync. | ADR documents safe approach. | Docs review. | External conflicts missed. |
| P3-012 | P3 | Add manual admin override workflow. | Force booking/cancel with audit trail. | Frontend UI. | Overrides are explicit and audited. | API tests. | Support cannot resolve edge cases. |
| P3-013 | P3 | Add integration reconciliation job. | Detect stale SMS/calendar outbox records. | Provider-specific repair UI. | Stale records are reported/retried. | Worker tests. | Integration drift accumulates. |
| P3-014 | P3 | Write two-way calendar sync ADR. | Risks, source of truth, conflict policy. | Implementation. | ADR rejects or scopes two-way sync safely. | Docs review. | Calendar becomes competing source of truth. |

### PRIORITY 4 - SaaS model and scale

| ID | Priority | Goal | Scope | Out | Acceptance | Validation | Risk |
|----|----------|------|-------|-----|------------|------------|------|
| P4-001 | P4 | Audit product multi-tenancy queries. | Review every product query for tenant filters. | Foundation audit. | Query audit checklist is complete. | Security review/tests. | Cross-tenant data leakage. |
| P4-002 | P4 | Add product tenant guards. | Middleware/dependencies/helpers for product APIs. | RLS migration. | Product APIs consistently require tenant context. | API/security tests. | Missing guard exposes data. |
| P4-003 | P4 | Add cross-tenant leakage tests. | All product APIs tested for denial. | Manual review only. | Every product route has isolation coverage. | `make validate`. | Isolation regressions merge. |
| P4-004 | P4 | Add self-service salon onboarding. | Signup/setup business profile. | Billing. | New salon can start setup safely. | API tests. | Manual onboarding limits scale. |
| P4-005 | P4 | Add onboarding wizard API. | Staff/service/hours guided setup endpoints. | Frontend. | Setup flow can be completed by API. | API tests. | Configuration remains error-prone. |
| P4-006 | P4 | Add phone provisioning workflow. | Reserve/assign provider numbers. | BYO phone porting. | Number lifecycle is tracked. | Adapter tests. | Phone setup remains manual/unreliable. |
| P4-007 | P4 | Add Stripe Billing model. | Subscription/customer/price linkage. | Deposit payments. | Salon subscription state is stored. | Model/webhook tests. | SaaS cannot monetize. |
| P4-008 | P4 | Add plans and limits. | Feature limits by plan. | Entitlement UI. | Limits are enforceable in service layer. | Service tests. | Overuse or surprise blocking. |
| P4-009 | P4 | Add billing webhooks. | Idempotent Stripe subscription events. | Checkout frontend. | Subscription state updates from webhooks. | Webhook tests. | Billing state drifts. |
| P4-010 | P4 | Block after plan limit exceeded. | Enforce booking/staff/service/feature limits. | Sales override UI. | Exceeded plans fail with clear errors. | API tests. | Revenue leakage or bad UX. |
| P4-011 | P4 | Add backward compatibility checklist. | Migration/versioning policy for existing salons. | Full API versioning rewrite. | Changes include compatibility review. | Docs/policy review. | Existing salons break on release. |

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
