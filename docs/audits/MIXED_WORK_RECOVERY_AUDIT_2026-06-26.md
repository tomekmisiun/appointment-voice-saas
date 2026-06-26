# Mixed Work Recovery Audit

**Date:** 2026-06-26
**Snapshot branch:** `backup/mixed-work-before-recovery-2026-06-26`
**Base branch:** `main`
**Status:** Recovery plan — do not merge the snapshot branch directly

---

## 1. Executive summary

The snapshot branch `backup/mixed-work-before-recovery-2026-06-26` contains work from at
least seven distinct tasks that were accumulated on a single dirty branch before a recovery
operation was initiated. The snapshot holds 94 changed files and approximately 8 000 added
lines relative to `main`.

Six of those seven tasks share a linear Alembic migration chain inside the snapshot. That
chain is an artifact of the branch contamination, not a reflection of true domain
dependencies. Telephony and demo, in particular, do not depend on SAC-009 at the domain
level — their migrations must be reconstructed on their own branches with `down_revision`
pointing to the correct head at the time each branch is created.

**The snapshot branch must not be merged directly.** Each task must be extracted onto a
fresh branch rebased on the current `main`, reviewed independently, and merged in a
dependency-safe order.

---

## 2. Snapshot context

| Property | Value |
|---|---|
| Snapshot branch | `backup/mixed-work-before-recovery-2026-06-26` |
| Snapshot HEAD | `1ba87f5` |
| Base branch | `main` |
| `main` HEAD migration | `sac003a2b3c4d5e6` |
| Files changed | 94 |
| Lines added | ~8 089 |
| Lines removed | ~306 |

---

## 3. Commits included in the snapshot

```
1ba87f5  chore: snapshot mixed work before recovery           <- HEAD of snapshot / monolithic contamination commit
a7bf6a1  feat(sac-006): staff profile lifecycle               <- clean SAC-006 only (9 files)
389d1b4  fix(sac-005): address reviewer findings
fe12efb  feat(sac-005): make business_memberships authoritative for RBAC
```

The commit `1ba87f5` is the root cause of the contamination. It absorbed SAC-007, SAC-008b,
SAC-009, telephony, demo, Railway config, and all frontend additions into a single snapshot
commit (76 files). The commit `a7bf6a1` is a clean, focused SAC-006 commit with exactly 9
files (the migration, staff model, audit log, schemas, staff service, and their tests).
Local branch names (`feat/sac-007-*`, `feat/sac-009-*`, `feat/telephony-*`, etc.) were all
pointing to `a7bf6a1` at the time the snapshot was taken, meaning those branches had not yet
received commits for their respective tasks — all that work landed in `1ba87f5` instead.

---

## 4. Current Alembic migration chain

The snapshot branch contains the following migration chain, all descending from the current
`main` head:

```
sac003a2b3c4d5e6        <- main HEAD (business_memberships table, SAC-003)
  └─ a353d8c535c7       SAC-006   staff profile fields + audit target_staff_id
       └─ 16050420530e  SAC-007   staff_service_assignments table
            └─ sac008b_cfk_ssa    SAC-008b  composite FKs on staff/service
                 └─ sac009_staff_inv        SAC-009   staff_invitations table
                      └─ avs_tel_status_pn  Telephony  telephony_status + business_phone_numbers
                           └─ avs_demo_user Demo       is_demo_user flag on users
```

This chain is linear with no branching heads inside the snapshot.

**Important correction — migration chain vs. domain dependency:**
The fact that `avs_tel_status_pn` lists `sac009_staff_inv` as its `down_revision` is
accidental. It reflects the order in which files were created on a shared dirty branch, not
a real schema dependency. The telephony migration only adds columns to `businesses` and
creates `business_phone_numbers` — it requires neither the `staff_invitations` table nor
any SAC-009 schema construct.

When the telephony feature is extracted onto its own branch, its migration should set
`down_revision` to the head of the base branch at that time (e.g. `sac003a2b3c4d5e6` if
no other migrations have landed yet, or the new head after SAC-006 and SAC-007 land if
those go first). The same applies to the demo (`avs_demo_user`) migration.

**Do not ship SAC-009 prematurely just to preserve the accidental migration chain.**

---

## 5. Change groups

### 5.1 SAC-005 — Membership RBAC

**Goal:** Make `business_memberships` the authoritative source for RBAC on all
business-scoped mutations. Replace `require_role("admin")` on every business route with
`require_business_member(OWNER, ADMIN)`. Create OWNER memberships automatically on signup,
business creation, and onboarding.

**Key files:**
- `app/api/dependencies/membership.py` (new)
- `app/services/membership_service.py` (new)
- `app/services/tenant_service.py` — `create_owner_membership` in `signup_tenant`
- `app/api/routes/businesses.py` — `create_owner_membership` in `create_business_endpoint`
- `app/api/routes/onboarding.py` — `create_owner_membership` in `onboarding_setup`
- Route files modified: `bookings`, `services`, `availability_exceptions`, `working_hours`,
  `business_transfer_hours`, `recurring_staff_blocks`, `clients`
- `tests/test_membership_rbac.py` (new)
- Test adaptations: `test_avs_i001_transfer_hours`, `test_avs_j002_smoke_manual_booking`,
  `test_avs_j004_smoke_cancellation`, `test_avs_p1004_admin_reschedule`,
  `test_avs_p3001_salon_hours_api`, `test_avs_p3004_staff_blocks`,
  `test_avs_p3005_recurring_staff_blocks`, `test_avs_p3008_pending_payment_state`,
  `test_avs_p3012_admin_override`, `test_booking_audit`
- `tests/test_fix_tenant_business_scoping.py` — adds `_give_admin_membership` helper

**Migration dependency:** None — uses existing `sac003a2b3c4d5e6` tables.

**Status:** Complete. Already pushed to `origin/feat/sac-005-membership-rbac-context`.

**Security:** `assert_active_business_role` filters by `tenant_id` from the authenticated
user. Platform admin bypass is explicit and limited to `User.role == "platform_admin"`.

**Recommended branch:** `feat/sac-005-membership-rbac-context` (already on origin)

---

### 5.2 SAC-006 — Staff profile lifecycle

**Goal:** New staff profile fields (`contact_email`, `position`, `accepts_bookings`,
`is_customer_visible`), soft deactivate/reactivate with audit log entries, and
`target_staff_id` column on `audit_logs`. Includes the SAC-008 employee management view
(enriched list/detail with membership status and calendar provider) because they share the
`StaffDetailRead` schema.

**Key files:**
- `alembic/versions/a353d8c535c7_sac006_staff_profile_fields_and_audit_.py` (new)
- `app/models/staff.py` — 5 new columns
- `app/models/audit_log.py` — 4 new `AuditAction` values, `target_staff_id` column
- `app/services/staff_service.py` — `deactivate_staff`, `reactivate_staff`,
  `list_staff_detail`, `get_staff_detail`, batch membership/calendar helpers
- `app/schemas/staff.py` — extended `StaffCreate`/`StaffRead`/`StaffUpdate`, new `StaffDetailRead`
- `app/api/routes/staff.py` — `POST /{id}/deactivate`, `POST /{id}/reactivate`,
  list/detail now return `StaffDetailRead`
- `tests/test_sac006_staff_profile_lifecycle.py` (new)
- `tests/test_sac008_employee_management_api.py` (new)

**Migration dependency:** `sac003a2b3c4d5e6` (main head) as `down_revision`.

**Status:** Complete.

**Breaking change:** `GET /businesses/{id}/staff` and `GET /businesses/{id}/staff/{id}`
now require `require_business_member(OWNER, ADMIN)` instead of the previous
`get_current_user`. Any client using these endpoints with a `user` role and no explicit
membership will receive HTTP 403. The IVR is unaffected because it calls
`get_eligible_transfer_staff` directly at the service layer.

**Recommended branch:** `feat/sac-006-staff-profile-lifecycle`

---

### 5.3 SAC-007 / SAC-008b — Staff service assignments

**Goal:** Join table linking staff members to the services they can perform. DB-level
composite foreign keys guarantee that a staff member and a service referenced by an
assignment belong to the same business. Integration into `availability_service` and
`booking_service` so that availability queries and booking creation validate whether a
given staff member is assigned to the requested service.

**Key files:**
- `alembic/versions/16050420530e_sac007_staff_service_assignments.py` (new)
- `alembic/versions/sac008b_composite_fk_staff_service_assignments.py` (new)
- `app/models/staff_service_assignment.py` (new)
- `app/services/staff_service_assignment_service.py` (new)
- `app/api/routes/staff_service_assignments.py` (new)
- `app/schemas/staff_service_assignment.py` (new)
- `app/models/service.py` — `uix_services_business_id_id` unique index (required FK target)
- `app/services/availability_service.py` — `staff_can_perform_service` integration
- `app/services/booking_service.py` — `staff_can_perform_service` integration
- `app/api/v1.py` — registers `staff_service_assignments_router`
- `tests/test_sac007_staff_service_assignments.py` (new)

**Migration dependency:** In the snapshot the SAC-007 migration descends from SAC-006
(`a353d8c535c7`). On a fresh branch its `down_revision` should point to whatever head is
current when the branch is created.

**Status:** Complete.

**Behavioral note:** `staff_can_perform_service` returns `True` when a staff member has no
assignments at all (backward-compatible opt-in). Once the first assignment is created,
the staff member is restricted to assigned services only. In `availability_service`, a
staff/service mismatch now returns an empty slot list rather than `NotFoundError` — a
semantic change that may surprise callers expecting HTTP 404.

**Recommended branch:** `feat/sac-007-staff-service-assignments`

---

### 5.4 SAC-009 — Staff invitations

**Goal:** Staff invitation model with HMAC SHA-256 token (only the hash stored in DB),
partial unique index for active invitations per `(business_id, staff_id, email)`, and
composite foreign keys ensuring cross-business drift is rejected at the database level.

**Key files:**
- `alembic/versions/sac009_staff_invitations.py` (new)
- `app/models/staff_invitation.py` (new)
- `app/services/staff_invitation_service.py` (new) — token generation/verify, create,
  resend, revoke, accept, expire sweep
- `app/models/business_membership.py` — `uix_business_memberships_business_id_id` index
  (required as FK target for `accepted_membership_id`)
- `tests/test_sac009_staff_invitation_model.py` (new)

**Migration dependency:** In the snapshot the SAC-009 migration descends from SAC-008b.
On a fresh branch its `down_revision` must be set independently.

**Status:** INCOMPLETE — model and service layer are implemented but there is no
`app/api/routes/staff_invitations.py` and the router is not registered in `app/api/v1.py`.
The feature is not reachable by any HTTP client.

**Security quality of existing implementation:**
- 256-bit CSPRNG token, only SHA-256 hex digest in DB, constant-time comparison. Good.
- Partial unique index prevents duplicate active invitations. Good.
- Expired invitations are freed automatically in `create_invitation`. Good.
- `INVITATION_GRANTABLE_ROLES` excludes `owner`. Good.

**Recommended branch:** `feat/sac-009-staff-invitation-model` — treat as WIP; merge only
after HTTP routes and `v1.py` registration are added.

---

### 5.5 Telephony status and phone numbers

**Goal:** `telephony_status` lifecycle field on businesses (`demo`, `pending_activation`,
`active`, `suspended`). New `business_phone_numbers` table for inbound number routing.
IVR webhook now rejects calls for businesses that are not in `active` state. SMS routing
uses a `DemoSmsProvider` for `demo`/`pending_activation` businesses so the full booking
flow can be tested without consuming real Twilio credits.

**Key files:**
- `alembic/versions/avs_telephony_status_phone_numbers.py` (new)
- `app/models/business.py` — `TelephonyStatus` enum, `telephony_status` column
- `app/models/business_phone_number.py` (new)
- `app/services/business_service.py` — `get_business_by_inbound_phone`,
  `assign_phone_number`, `list_phone_numbers`
- `app/api/routes/businesses.py` — `GET/POST /{business_id}/phone-numbers` endpoints
- `app/schemas/business.py` — `BusinessPhoneNumberRead`
- `app/api/routes/twilio_voice.py` — rejects inbound calls when `telephony_status != ACTIVE`
- `app/services/sms_provider.py` — `DemoSmsProvider`, `get_sms_provider_for_business`
- `app/services/notification_service.py` — business-aware SMS routing
- `tests/test_telephony_status_and_phone_numbers.py` (new)
- `tests/test_avs_p1008_ivr_backend_unavailable.py` — adds `telephony_status=ACTIVE`
- `tests/test_twilio_voice_webhook.py` — adds `telephony_status=ACTIVE` to fixtures;
  adds rejection tests for `demo` and `suspended` businesses
- `frontend/features/dashboard/components/TelephonyStatusCard.tsx` (new)
- `frontend/features/dashboard/components/TelephonyStatusCard.test.tsx` (new)
- `frontend/features/dashboard/components/CopyButton.tsx` (new)
- `frontend/app/dashboard/page.tsx` — renders `TelephonyStatusCard`
- `frontend/features/bookings/components/BookingsListClient.test.tsx` — adds
  `telephony_status` field to test fixture

**Migration dependency:** In the snapshot the telephony migration has `down_revision =
"sac009_staff_inv"`. This is accidental. On a fresh branch the migration should descend
from whatever head is current, independently of SAC-009.

**Status:** Complete, modulo the race condition described in section 6.

**Auth note:** `assign_phone_number_endpoint` uses `require_role("admin")` (platform-level
admin), not `require_business_member`. This means phone number assignment is restricted to
operators, not business owners. This is intentional per the provisioning runbook.

**Recommended branch:** `feat/telephony-status-and-phone-numbers`

---

### 5.6 Public demo read-only

**Goal:** `POST /api/v1/auth/demo` issues JWT tokens for a pre-seeded demo user without a
password. Requires `PUBLIC_DEMO_ENABLED=true` in the environment. The demo user
(`is_demo_user=True`) can view the dashboard but all write endpoints are blocked
server-side by `require_non_demo_user`.

**Key files:**
- `alembic/versions/avs_demo_user_flag.py` (new)
- `app/models/user.py` — `is_demo_user` boolean column
- `app/services/auth_service.py` — `create_demo_session`
- `app/api/routes/auth.py` — `POST /auth/demo` endpoint
- `app/core/config.py` — `public_demo_enabled` flag
- `app/seed_demo_data.py` — creates demo user, ADMIN membership, optional
  `BusinessPhoneNumber`; guard changed from `environment != "development"` to
  `environment == "production"` so staging can seed demo data
- `frontend/app/demo/page.tsx` (new)
- `frontend/app/api/auth/demo/route.ts` (new) — Next.js BFF proxy with CSRF protection
- `frontend/app/page.tsx` — homepage CTA changed from `/register` to `/demo`
- `tests/test_avs_demo_access.py` (new)

**Migration dependency:** In the snapshot `avs_demo_user` has `down_revision =
"avs_tel_status_pn"` because it was created after the telephony migration on the same
dirty branch. There is a genuine order dependency here: the demo migration adds
`is_demo_user` to `users`, and `seed_demo_data.py` sets `telephony_status = ACTIVE` on
the demo business — so in practice the demo feature needs the telephony migration to have
run. However, on a fresh branch both migrations can and should be developed together,
either as a single migration or with the demo migration depending on the telephony one
explicitly.

**Status:** Complete.

**Recommended branch:** `feat/public-demo-workspace`

---

### 5.7 Demo mutation guards

**Goal:** `require_non_demo_user` FastAPI dependency that raises HTTP 403 for any user
with `is_demo_user=True`, applied to every state-mutating endpoint.

**Coverage — all write endpoints audited:**

| Endpoint group | Guard applied |
|---|---|
| POST/override/cancel/reschedule/refund bookings | Yes |
| POST/PATCH/DELETE services | Yes |
| POST staff, PATCH staff, POST deactivate/reactivate | Yes |
| POST/DELETE availability exceptions | Yes |
| POST/PATCH/DELETE working hours | Yes |
| POST/DELETE transfer hours | Yes |
| POST/DELETE recurring staff blocks | Yes |
| POST/PATCH clients | Yes |
| POST files (upload, presigned, complete, delete) | Yes |
| POST onboarding setup | Yes |
| PATCH owner lead status | Yes |
| POST/PATCH admin tenants | Yes |
| PATCH/DELETE/deactivate/activate users | Yes |
| POST customers GDPR delete | Yes |
| POST/DELETE staff service assignments | Yes |
| Twilio webhooks | No guard — correct (Twilio signature is the auth boundary) |

No gaps found in the current endpoint set.

**Recommended branch:** `feat/public-demo-workspace` (ship together with 5.6)

---

### 5.8 Railway deployment

**Goal:** Railway configuration files for backend (Dockerfile-based) and frontend
(Nixpacks), plus pnpm workspace adjustment needed for Railway's build detection.

**Key files:**
- `railway.toml` (new) — backend: Dockerfile builder, `alembic upgrade head` as release
  command, uvicorn as start command
- `frontend/railway.toml` (new) — frontend: Nixpacks, `pnpm exec next start`
- `frontend/.node-version` (new) — pins Node 22
- `frontend/pnpm-workspace.yaml` — adds `packages: ["."]` to declare the frontend root
  as a workspace package
- `.env.example` — adds commented Twilio and demo environment variables

**Migration dependency:** None. Fully independent.

**Note on `pnpm-workspace.yaml`:** Adding `packages: - "."` alongside the existing
`allowBuilds` and `minimumReleaseAgeExclude` fields is valid YAML. The root `Dockerfile`
already exists on `main`, so `railway.toml` referencing it is correct. The `packages`
field change should be verified in a Railway staging build before merging to production.

**Status:** Complete.

**Recommended branch:** `feat/railway-deployment` — independent, can be merged at any time

---

### 5.9 OpenAPI and generated types

**Key files:**
- `frontend/lib/api/openapi.json` — fully regenerated (1 270 lines changed)
- `frontend/lib/api/schema.gen.ts` — fully regenerated (599 lines changed)
- `frontend/lib/api/types.ts` — manual addition of `BusinessPhoneNumberRead` type export

**Status:** The `openapi.json` and `schema.gen.ts` in the snapshot represent the state
after all seven tasks were applied simultaneously. They should not be copied from the
snapshot. Each feature branch must regenerate these files after its own backend changes
land, then commit the regenerated output alongside the backend PR.

The manual `types.ts` export can be restored selectively when the telephony branch lands.

**Recommended action:** Regenerate per feature branch. Do not restore from snapshot.

---

### 5.10 Documentation and frontend UI

**Key files:**
- `docs/audits/TELEPHONY_DEMO_AUDIT.md` (new, 622 lines) — pre-implementation audit
  written before any telephony code existed; references correct endpoints
- `docs/telephony/DEMO_AND_NUMBER_PROVISIONING.md` (new, 201 lines) — operator runbook
  for the telephony lifecycle

Both documents are written in clean UTF-8 with no encoding issues. They accurately describe
the implemented endpoints. SAC-009 invitation endpoints are not described (consistent with
the fact that no HTTP routes exist).

Frontend UI components (`TelephonyStatusCard`, `CopyButton`) belong with the telephony
feature branch.

---

## 6. Critical findings

### F1 — Race condition in `assign_phone_number` — possible HTTP 500

**Location:** `app/services/business_service.py`, function `assign_phone_number`

The service performs an application-level uniqueness check on `phone_number` and
`provider_number_sid` before inserting a new `BusinessPhoneNumber` row. Between the read
and the insert, a concurrent request can violate the unique constraints defined on those
columns. SQLAlchemy will raise an unhandled `IntegrityError` which propagates as HTTP 500
instead of a controlled HTTP 409 `ConflictError`.

**Fix required:** Wrap the insert and commit in a `try/except IntegrityError` block and
convert to `BadRequestError` or `ConflictError`.

---

### F2 — SAC-009 has no HTTP API — feature is not reachable

**Location:** `app/services/staff_invitation_service.py` exists;
`app/api/routes/staff_invitations.py` does not exist; `app/api/v1.py` does not register
any invitation router.

The model and service layer are fully implemented but the feature is completely unreachable
by any HTTP client. SAC-009 must not be treated as complete and must not be merged until
HTTP routes and `v1.py` registration are added.

---

### F3 — Breaking auth change on staff read endpoints

**Location:** `app/api/routes/staff.py`

`GET /businesses/{business_id}/staff` and `GET /businesses/{business_id}/staff/{staff_id}`
previously required only `get_current_user` (any authenticated user). After the SAC-006
change they require `require_business_member(OWNER, ADMIN)`. Any frontend page, test, or
external client that calls these endpoints with a `user` role and no explicit membership
record will receive HTTP 403 instead of the expected response.

The IVR system is unaffected because it uses `get_eligible_transfer_staff` directly via
the service layer.

---

### F4 — All existing businesses get `telephony_status = 'demo'` after migration

**Location:** `alembic/versions/avs_telephony_status_phone_numbers.py`

The migration adds `telephony_status` to `businesses` with `server_default = 'demo'`.
Every existing business row will be stamped `demo` after `alembic upgrade head` runs.
The Twilio voice webhook now rejects inbound calls for businesses where
`telephony_status != ACTIVE`. This means production businesses that previously received
real calls will silently stop receiving them until an operator sets `telephony_status =
'active'` for each affected business.

**Required before deploying this migration to production:** A data migration or operator
runbook that sets `telephony_status = 'active'` for every business that already has an
active Twilio number.

---

### F5 — Demo session has no cap on the number of active sessions

**Location:** `app/services/auth_service.py`, `create_demo_session`

Every call to `POST /api/v1/auth/demo` generates a new access/refresh token pair. The
rate limiter (`auth_login_rate_limit`) throttles the call rate but does not cap the total
number of valid refresh tokens in circulation. With a 7-day refresh token TTL, sustained
rate-limited calls can accumulate a large number of active sessions. There is no bulk
revocation mechanism other than incrementing the demo user's `token_version`.

This is not a runtime error risk but is a potential abuse vector. A follow-up should
consider limiting concurrent demo sessions per source IP, or adding a session count cap.

---

### F6 — OpenAPI contracts must be regenerated per feature branch

The `frontend/lib/api/openapi.json` and `frontend/lib/api/schema.gen.ts` in the snapshot
reflect the combined state of all seven tasks. They should not be copied as-is onto any
individual feature branch. Doing so would introduce forward declarations for endpoints that
do not exist on that branch, which will cause TypeScript errors and mislead reviewers.

Each feature branch must generate its own OpenAPI snapshot immediately before the PR is
opened.

---

### F7 — Snapshot branch must not be merged directly

The snapshot commit `1ba87f5` on `backup/mixed-work-before-recovery-2026-06-26` is a
single point that contains seven unreviewed tasks with at least two incomplete ones (SAC-009
has no HTTP API) and one with a critical bug (race condition in `assign_phone_number`). A
direct merge would introduce all of these problems at once with no granular review trail.

---

## 7. Migration recovery strategy

The migration chain in the snapshot (`sac009_staff_inv` -> `avs_tel_status_pn` ->
`avs_demo_user`) is an accidental artifact of working on a shared dirty branch. It does not
reflect real schema dependencies between those features.

**When reconstructing each feature branch:**

1. Do not copy migration files from the snapshot verbatim.
2. Generate a new migration on each feature branch with `alembic revision --autogenerate`
   (or create manually), setting `down_revision` to the current head of `main` at the time
   the branch is created.
3. The telephony migration (`avs_telephony_status_phone_numbers.py`) does not depend on any
   SAC-009 schema. Its `down_revision` on a fresh branch should point to whatever head is
   current after the preceding feature branches have landed.
4. The demo migration (`avs_demo_user_flag.py`) adds `is_demo_user` to `users`. It has a
   soft dependency on the telephony migration only because `seed_demo_data.py` sets
   `telephony_status = 'active'` on the demo business — these two migrations can be shipped
   together or the demo migration can depend on the telephony migration explicitly.
5. The SAC-009 migration (`sac009_staff_invitations.py`) must not be placed in the chain
   before telephony and demo simply to preserve the accidental snapshot order.

---

## 8. Recommended recovery order

This order reflects domain readiness and review risk, not the accidental migration chain
in the snapshot. It is not required that every step land before the next begins — parallel
PRs are possible as long as migration `down_revision` values do not conflict.

### Step 1 — SAC-005 Membership RBAC

Already on `origin/feat/sac-005-membership-rbac-context`. Open a PR from the existing
remote branch. Include the test fixture adaptations (`test_fix_tenant_business_scoping.py`
and all `test_avs_*` test files that add `_give_admin_membership` calls).

### Step 2 — SAC-006 Staff profile lifecycle (+ SAC-008 employee management view)

Extract onto a fresh branch from `main` after SAC-005 merges. Include the SAC-006
migration, staff model changes, audit log additions, service functions
(`deactivate_staff`, `reactivate_staff`, `list_staff_detail`, `get_staff_detail`),
schemas, and routes. SAC-008 shares the `StaffDetailRead` schema and should ship on the
same branch.

### Step 3 — SAC-007 / SAC-008b Staff service assignments

Extract onto a fresh branch after SAC-006 merges (SAC-006 fields are referenced in tests
and the availability/booking integrations). Include both migration files, the model,
service, route, schema, and the integrations in `availability_service` and
`booking_service`.

### Step 4 — Telephony status and phone numbers

Extract onto a fresh branch. Fix the race condition in `assign_phone_number` (finding F1)
before opening the PR. Write a data migration or operator runbook for existing businesses
(finding F4). Migrate with `down_revision` pointing to the then-current head.

### Step 5 — Public demo read-only (+ demo mutation guards)

Extract onto a fresh branch after the telephony migration lands. Includes the
`avs_demo_user_flag` migration, `is_demo_user` model field, `create_demo_session`,
`POST /auth/demo` endpoint, `require_non_demo_user` dependency and all route applications,
`seed_demo_data.py` changes, frontend demo page and BFF route.

### Step 6 — SAC-009 Staff invitations (after HTTP API is added)

Do not restore SAC-009 until `app/api/routes/staff_invitations.py` and the `v1.py`
registration are written and reviewed. Once the HTTP layer is complete, extract the
migration, model, service, and new routes onto a fresh branch. The `down_revision` for
the SAC-009 migration should point to whatever the current main head is at that time — not
the SAC-008b revision from the snapshot.

### Step 7 — Railway deployment (independent)

This branch can be opened and merged at any point, independently of all other tasks. No
schema changes. No application logic changes.

---

## 9. Files and changes not to restore directly

| File or fragment | Reason |
|---|---|
| `frontend/lib/api/openapi.json` from snapshot | Regenerated artefact combining all seven tasks. Must be regenerated per feature branch. |
| `frontend/lib/api/schema.gen.ts` from snapshot | Same as above. |
| `alembic/versions/sac009_staff_invitations.py` | Must not be placed in a deployable migration chain until SAC-009 HTTP routes exist. |
| `alembic/versions/avs_telephony_status_phone_numbers.py` verbatim | Must be recreated with a corrected `down_revision` on the telephony branch. |
| `alembic/versions/avs_demo_user_flag.py` verbatim | Must be recreated with a corrected `down_revision` on the demo branch. |
| Snapshot commit `1ba87f5` | Contains the bulk of the contamination: 76 files covering SAC-007, SAC-008b, SAC-009, telephony, demo, Railway, and all frontend additions. Must not be cherry-picked or merged as a unit. Extract individual features from it selectively. |
| `assign_phone_number` in `business_service.py` | Must be restored with the `IntegrityError` race condition fixed before merging the telephony branch. |

---

## 10. Recovery rules

- Never merge `backup/mixed-work-before-recovery-2026-06-26` directly.
- Reconstruct every feature on a fresh branch created from the current `main`.
- Restore shared files selectively, preferably with `git restore -p`.
- Do not copy generated OpenAPI files from the snapshot.
- Regenerate Alembic migrations on the correct feature branch with the correct `down_revision`.
- Run targeted tests before full validation.
- One task must result in one branch and one independently reviewable PR.
