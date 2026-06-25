# Staff Access and Calendar: Current-State Audit

- **Date:** 2026-06-24
- **Scope:** authentication, tenancy, staff, authorization, scheduling,
  bookings, internal calendar data, and external calendar integrations
- **Change type:** documentation only; no runtime behavior was changed
- **Evidence rule:** every statement about current behavior names a concrete
  file or symbol. Line numbers are intentionally omitted because symbols are
  more stable across implementation branches.

## Status vocabulary

- **Existing**: verified in the current repository.
- **Recommended**: target design, not implemented.
- **Required**: mandatory before staff access can be enabled safely.
- **Optional**: useful but not required for the first release.
- **Deferred**: explicitly outside MVP.

## Executive finding

The repository has a useful scheduling foundation, but it does not yet have a
staff identity/access model. `Staff` and `User` are separate records, but there
is no relationship between them and no membership table. A `User` belongs
directly to exactly one `Tenant`; its tenant-wide role is stored on the user.
The current `user` role can read every staff member and booking in a business,
so it cannot safely be renamed to `staff`.

The internal calendar data already exists as `WorkingHours`,
`AvailabilityException`, `RecurringStaffBlock`, and `Booking`. There is no
calendar read model or employee-facing calendar API/UI. External calendar code
is outbound-only and uses a null or fake provider. There is no Google OAuth,
ICS ingestion, encrypted credential storage, or external busy-period model.

## Current architecture

### Authentication and tenant resolution

- **Existing:** login is tenant-aware. `POST /api/v1/auth/login` resolves a
  tenant before authenticating an email/password pair
  (`app/api/routes/auth.py:login`, `app/api/dependencies/tenant.py`,
  `app/services/auth_service.py:login_user`). The frontend supplies workspace
  context through its auth BFF (`frontend/app/api/auth/login/route.ts`).
- **Existing:** access and refresh JWTs contain `sub`, `tenant_id`,
  `token_version`, `type`, expiry, and refresh `jti`; they do not contain a
  role, business, membership, or staff identifier
  (`app/core/security.py:create_access_token`, `create_refresh_token`).
- **Existing:** `get_current_user()` loads the user using both JWT user and
  tenant IDs, verifies activity/token version, and optionally verifies
  `X-Tenant-Slug` (`app/api/dependencies/auth.py:get_current_user`). Role checks
  therefore use fresh database state rather than trusting a role claim.
- **Existing:** login/register/password-reset endpoints have Redis-backed rate
  limit dependencies (`app/api/routes/auth.py`,
  `app/api/dependencies/rate_limit.py`).
- **Gap:** there is no authenticated active-membership selection. Workspace is
  effectively fixed by `User.tenant_id`.

### Tenant, business, user, and membership

- **Existing:** `Tenant` is the workspace boundary and has a globally unique
  slug (`app/models/tenant.py:Tenant`).
- **Existing:** `Business` is tenant-scoped and stores operational salon data,
  including timezone (`app/models/business.py:Business`). A tenant can have
  multiple businesses because no one-to-one constraint exists.
- **Existing:** `User` has non-null `tenant_id`, email, password hash, active
  state, role, and token version. `(tenant_id, email)` is unique
  (`app/models/user.py:User`). Email is not globally unique.
- **Missing:** there is no `Membership` SQLAlchemy model or table.
  `app/services/tenant_membership_service.py` only validates the direct
  `User.tenant_id` relationship and active tenant; its name does not indicate
  a persisted membership.
- **Existing:** public tenant signup creates the first user with role `admin`,
  not `owner` (`app/api/routes/signup.py:signup`,
  `app/services/tenant_service.py:signup_tenant`).

### Staff domain

- **Existing:** `Staff` is a tenant/business-scoped business record with name,
  optional phone, active state, and created timestamp
  (`app/models/staff.py:Staff`). It can exist without a user account because it
  has no user foreign key.
- **Existing:** bookings, working hours, exceptions, recurring blocks, and
  calendar integrations can reference `staff_id`
  (`app/models/booking.py:Booking`, `app/models/working_hours.py:WorkingHours`,
  `app/models/availability_exception.py:AvailabilityException`,
  `app/models/recurring_staff_block.py:RecurringStaffBlock`,
  `app/models/calendar_integration.py:CalendarIntegration`).
- **Gap:** staff has no contact email, position, customer visibility,
  bookability flag, access status, or user/membership link
  (`app/models/staff.py`, `app/schemas/staff.py`).
- **Gap:** there is no staff-service assignment table; `Service` has no staff
  relationship (`app/models/service.py:Service`).
- **Existing:** admin-only create/update and authenticated list/read endpoints
  are exposed below `/businesses/{business_id}/staff`
  (`app/api/routes/staff.py`). Service queries scope by tenant and business
  (`app/services/staff_service.py`).

### Roles and authorization

- **Existing:** roles are `user`, `admin`, and `platform_admin` with static
  permissions/hierarchy (`app/core/permissions.py`, `app/schemas/user.py`).
- **Existing:** authorization is enforced in FastAPI dependencies
  `require_permission()` and `require_role()`
  (`app/api/dependencies/auth.py`).
- **Existing:** an admin can update another user's role using
  `UserAdminUpdate.role`; a role change increments `token_version`
  (`app/api/routes/users.py:patch_user`,
  `app/services/user_service.py:update_user`).
- **Gap:** owner/admin/staff semantics do not exist. Billing/ownership actions
  therefore cannot be separated from operational admin actions.
- **Risk:** `list_staff_endpoint`, `get_staff_endpoint`,
  `list_bookings_endpoint`, and `get_booking_endpoint` require only an
  authenticated user (`app/api/routes/staff.py`,
  `app/api/routes/bookings.py`). A future staff account would consequently be
  able to enumerate coworkers and their bookings unless these routes change.

### Tenant and business isolation

- **Existing:** product services generally filter by `tenant_id` and
  `business_id`; regression coverage exists in
  `tests/test_fix_tenant_business_scoping.py`, `tests/test_tenancy.py`,
  `tests/test_tenant_isolation.py`, and `tests/test_product_tenant_isolation.py`.
- **Existing:** direct user access is tenant-scoped in
  `app/services/user_service.py:get_user_by_id` and permission helpers require
  shared tenant (`app/services/permission_service.py`).
- **Gap:** there is no per-business membership. Any user in a tenant can use
  read endpoints for any business in that tenant when those endpoints require
  only `get_current_user`. Current service-layer business checks prevent
  cross-business object substitution, but not authorized discovery of another
  business within the same tenant.
- **Required:** target authorization must derive a business and employee scope
  from membership, never from a client-supplied employee identifier alone.

### Scheduling, availability, and bookings

- **Existing:** `WorkingHours` stores recurring business-wide or staff-specific
  windows (`app/models/working_hours.py:WorkingHours`).
- **Existing:** `AvailabilityException` stores exact-date closures or special
  hours and can target the business or one staff member
  (`app/models/availability_exception.py:AvailabilityException`). It is the
  current closest equivalent to one-off time off, but it has no approval or
  ownership lifecycle.
- **Existing:** `RecurringStaffBlock` stores recurring subtractive windows such
  as breaks (`app/models/recurring_staff_block.py:RecurringStaffBlock`,
  `docs/adr/0003-recurring-staff-blocks.md`).
- **Existing:** availability is computed, not persisted. The current order is
  working-hours intersection, exact-date exception replacement/closure,
  recurring-block subtraction, then active local-booking exclusion
  (`app/services/availability_service.py:_get_available_slots_for_duration`).
- **Existing:** confirmed and pending-payment bookings block slots; bookings
  have optional `staff_id` (`app/models/booking.py:Booking`,
  `app/services/availability_service.py`). PostgreSQL exclusion constraints
  prevent overlapping active bookings for a staff member
  (`alembic/versions/p3008_add_pending_payment_state.py`).
- **Gap:** there is no dedicated time-off model, manual one-off blocked-period
  model with ownership, or employee self-service endpoint.
- **Gap:** list bookings supports status/staff pagination but no date-range
  filter (`app/api/routes/bookings.py:list_bookings_endpoint`), which blocks an
  efficient week/agenda calendar query.

### Internal calendar

- **Existing:** all data required for a read-only local agenda is present in
  the scheduling and booking tables listed above.
- **Missing:** there is no internal `CalendarEvent` aggregate for local display.
  `app/models/calendar_event.py:CalendarEvent` is specifically an outbound
  provider-sync record, not a domain calendar event.
- **Missing:** no `/me/calendar` or staff-specific calendar read endpoint is
  registered (`app/api/v1.py`). No dashboard calendar page exists under
  `frontend/app/dashboard/`.
- **Recommended:** do not create a second booking/event source of truth. Build
  a calendar read projection from bookings plus schedule exclusions.

### External calendars

- **Existing:** `CalendarIntegration` selects one business-level or one
  staff-level provider/calendar destination; partial unique indexes enforce
  this (`app/models/calendar_integration.py`,
  `alembic/versions/b1c2d3e4f5a6_add_calendar_integrations.py`).
- **Existing:** `CalendarEvent` tracks outbound create/update/cancel attempts for
  one booking (`app/models/calendar_event.py`,
  `app/services/calendar_service.py`). Worker retry/reconciliation patterns are
  reusable (`app/worker.py`, `app/services/reconciliation_service.py`).
- **Existing:** `CalendarProvider` only supports create/update/cancel. Runtime
  resolution always returns `NullCalendarProvider`; `FakeCalendarProvider` is
  test-only support (`app/services/calendar_provider.py`).
- **Missing:** no Google provider/OAuth flow, ICS parser, inbound busy API,
  token refresh, integration API routes, external busy table, or encrypted
  persistence for provider credentials/private ICS URLs. Repository searches
  for OAuth/ICS/provider credential encryption find no backend implementation.
- **Conflict:** accepted ADRs 0005 and 0006 currently prohibit imported busy
  data from reducing offered availability. The requested target behavior needs
  a superseding ADR; it must continue to prohibit external events from
  creating, editing, or cancelling local bookings.
- **Documentation drift:** README claims a real Google Calendar provider is
  wired, but `get_calendar_provider()` returns only `NullCalendarProvider`.
  Runtime code is authoritative.

### Frontend and BFF

- **Existing:** encrypted HttpOnly session cookies hold backend JWTs
  (`frontend/lib/auth/session.ts`, `frontend/lib/auth/server.ts`).
- **Existing:** dashboard Server Components load `/auth/me` and businesses;
  auth failures redirect through refresh
  (`frontend/features/dashboard/current-business.ts`,
  `frontend/app/dashboard/layout.tsx`).
- **Existing:** BFF route handlers proxy booking/availability operations while
  keeping backend tokens server-side (`frontend/app/api/`).
- **Existing:** frontend role hierarchy mirrors backend `user/admin/platform_admin`
  (`frontend/lib/auth/roles.ts`).
- **Gap:** a single `AppShell`/navigation serves all roles
  (`frontend/components/layout/AppShell.tsx`, `nav-items.ts`). There is no staff
  route group, role-specific navigation, employee context, explicit forbidden
  page, or calendar UI.
- **Gap:** OpenAPI types are maintained locally in
  `frontend/lib/api/types.ts`; no generated client pipeline was found.

### Invitation, email, audit, and secrets

- **Existing reusable pattern:** password-reset tokens are random, hashed,
  expiring, one-time records (`app/models/password_reset_token.py`,
  `app/services/password_reset_service.py`, `app/core/security.py`).
- **Existing reusable pattern:** background jobs and email delivery exist for
  password reset (`app/services/email_service.py`, `app/worker.py`).
- **Missing:** no employee invitation table, endpoint, accept flow, resend,
  revoke, or invitation audit actions.
- **Missing:** no backend facility encrypts arbitrary database secrets such as
  OAuth refresh tokens or private ICS URLs. Frontend session AES-GCM in
  `frontend/lib/auth/session.ts` is not reusable backend-at-rest encryption.
- **Existing:** general audit logging exists (`app/models/audit_log.py`,
  `app/services/audit_log_service.py`), but actions do not cover membership,
  invitations, time off, or calendar integration lifecycle.

## Answers to architecture questions

| # | Answer | Evidence |
|---|--------|----------|
| 1 | **Yes, partially.** `Staff` and `User` are separate, but cannot be linked. | `app/models/staff.py:Staff`; `app/models/user.py:User` |
| 2 | **No.** The named membership service validates direct tenant ownership only. | `app/services/tenant_membership_service.py`; no membership model in `app/models/` |
| 3 | **No.** A user has one non-null `tenant_id`. | `app/models/user.py:User.tenant_id` |
| 4 | **Unique within tenant, not globally.** | `app/models/user.py:ix_users_tenant_id_email` |
| 5 | **On `users.role`.** | `app/models/user.py:User.role` |
| 6 | From JWT `tenant_id`; pre-auth workspace resolves tenant slug; optional header is cross-checked. | `app/api/dependencies/tenant.py`; `app/api/dependencies/auth.py:get_current_user` |
| 7 | JWT has `tenant_id`; it has no business/workspace/role/staff/membership claim. | `app/core/security.py:create_access_token` |
| 8 | **Yes.** Static backend dependencies enforce current roles/permissions. | `app/api/dependencies/auth.py`; `app/core/permissions.py` |
| 9 | **Yes across tenants; partial within a tenant's businesses.** Service scoping/tests exist, but no business membership exists. | `tests/test_fix_tenant_business_scoping.py`; `app/services/staff_service.py` |
| 10 | First signup user becomes `admin`, not `owner`. | `app/services/tenant_service.py:signup_tenant` |
| 11 | **Yes:** `staff`. | `app/models/staff.py`; domain migration `1a2b3c4d5e6f` |
| 12 | **Yes.** Staff has no user FK. | `app/models/staff.py` |
| 13 | **No.** Password reset offers a pattern, not an invitation system. | `app/models/password_reset_token.py`; no invitation route/model |
| 14 | **Indirectly.** Exact-date `AvailabilityException` can close staff time; no dedicated time-off lifecycle. | `app/models/availability_exception.py` |
| 15 | **Yes.** | `app/models/working_hours.py` |
| 16 | **Computed only.** No availability table; service computes slots. | `app/services/availability_service.py` |
| 17 | **Optionally.** | `app/models/booking.py:Booking.staff_id` |
| 18 | **Data foundation only.** No employee calendar API/read model/UI. | scheduling models; `app/api/v1.py`; `frontend/app/dashboard/` |
| 19 | **No real Google integration.** Only null/fake provider abstractions. | `app/services/calendar_provider.py:get_calendar_provider` |
| 20 | **No.** | no ICS model/parser/routes in `app/` |
| 21 | **No backend at-rest mechanism for these secrets.** | backend config/services; frontend-only `frontend/lib/auth/session.ts` |
| 22 | **Yes for outbound sync/reconciliation, not inbound import.** | `app/worker.py`; `app/services/reconciliation_service.py` |
| 23 | **Yes for current roles; no target roles exist on either side.** | `app/core/permissions.py`; `frontend/lib/auth/roles.ts` |
| 24 | **No known cross-tenant path in audited staff/booking services; tests cover it.** The future staff role would over-read within its own tenant/business. | tenant isolation tests; authenticated-only list routes |
| 25 | Reuse Staff, schedules, bookings, timezone, tenant-scoped service guards, password-reset token pattern, audit/outbox/worker/BFF patterns. | files cited in sections above |
| 26 | Membership/role backfill, owner inference, optional staff-user linking, staff metadata, service assignments, invitations, integration credentials, and busy periods require migrations. | current models/migrations above |
| 27 | **MVP:** membership/RBAC, staff linkage, invitations, own agenda/profile/time off. **Pilot:** ICS read-only busy. **Later:** Google read-only OAuth, write-back, drag/drop. | target spec and roadmap linked below |

## Existing test coverage

**Existing:** auth and RBAC tests (`tests/test_auth.py`,
`tests/test_permissions.py`, `tests/test_users.py`); tenant isolation tests
(`tests/test_tenancy.py`, `tests/test_tenant_isolation.py`,
`tests/test_product_tenant_isolation.py`,
`tests/test_fix_tenant_business_scoping.py`); staff/scheduling/booking tests
(`tests/test_staff.py`, `tests/test_working_hours.py`,
`tests/test_availability.py`, `tests/test_bookings.py`,
`tests/test_booking_concurrency.py`); calendar model/provider/service/worker
tests (`tests/test_calendar_integration.py`, `tests/test_calendar_provider.py`,
`tests/test_calendar_service.py`, `tests/test_worker.py`,
`tests/test_reconciliation_service.py`). Frontend tests cover auth, dashboard,
staff management, booking routes/components, and availability BFF routes.

**Missing:** membership lifecycle, owner/admin/staff matrix, staff self-scope,
invitation races/replay, employee-user uniqueness, own calendar/time-off,
external busy periods, ICS SSRF, OAuth state/refresh/revocation, stale-import
policy, and role-specific frontend route E2E tests.

## Confirmed gaps and contradictions

1. **Required:** introduce persisted membership and stop treating
   `User.tenant_id` plus `User.role` as the long-term authorization model.
2. **Required:** link at most one active membership to at most one staff record
   in a business, while preserving staff without login accounts.
3. **Required:** replace broad authenticated read routes with explicit
   owner/admin all-resource scope and staff self scope.
4. **Required:** define owner separately from operational admin before billing
   and ownership transfer are exposed.
5. **Required:** add invitation lifecycle and atomic acceptance.
6. **Required:** add date-bounded calendar reads and dedicated self endpoints.
7. **Required before ICS/OAuth:** add envelope encryption/key rotation design,
   SSRF-safe fetcher, audit events, and secret-safe logging.
8. **Required:** supersede ADR 0005/0006 only for read-only busy-period
   availability exclusion; never make external data authoritative for bookings.
9. **Recommended:** preserve the physical table name `staff` initially and
   treat “Employee” as product vocabulary to avoid a needless table rename.
10. **Deferred:** two-way booking write-back, drag-and-drop scheduling,
    calendar webhooks, multi-calendar aggregation, and approval workflows.

## Related decisions and plan

- Target specification: [Staff Access, Scheduling, and Calendar Integrations](../specs/staff-access-and-calendar.md)
- Identity decision: [ADR 0007](../adr/0007-separate-staff-records-from-login-identities.md)
- Calendar decision: [ADR 0008](../adr/0008-external-busy-periods-as-availability-exclusions.md)
- Executable epic: [Staff access and calendar roadmap](../product/staff-access-calendar-roadmap.md)

