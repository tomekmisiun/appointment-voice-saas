# Appointment Voice SaaS Backlog

This is the active executable backlog for VoxSlot product work. Completed
historical backlog detail is archived in
[`../archive/audits/appointment-saas-roadmap-legacy.md`](../archive/audits/appointment-saas-roadmap-legacy.md).

Use [`../../ROADMAP.md`](../../ROADMAP.md) for high-level sequencing and
[`../../TECH_DEBT.md`](../../TECH_DEBT.md) for active risk/debt detail.

## Current Repository Reality

- Core backend booking, IVR, SMS, waitlist, staff/services/hours, public demo,
  and worker flows are implemented.
- Frontend covers auth, demo, dashboard, bookings, and staff.
- Production readiness is not claimed.
- `BusinessMembership.role` exists but runtime auth still uses `User.role`.
- Real calendar OAuth/setup, billing, phone provisioning, public booking
  management links, and several owner configuration screens remain future work.

## Task Format

Each task should be implemented as one branch and one reviewable change.

| Field | Meaning |
|---|---|
| ID | Stable backlog identifier. |
| Priority | `P0` blocker, `P1` pilot-critical, `P2` important product, `P3` scale/commercial. |
| Goal | User or operator outcome. |
| Scope | What the task includes. |
| Out of scope | What must not be bundled. |
| Validation | Minimum proof before marking done. |

## Active Backlog

| ID | Priority | Goal | Scope | Out of scope | Validation |
|---|---|---|---|---|---|
| OPS-001 | P0 | Verify and repair production API health. | Check Railway API logs, config, migration/pre-deploy output, and `/health/live`/`/health/ready`. | Feature work unrelated to startup health. | Production health endpoint is reachable or the incident is documented with owner decision. |
| TEST-001 | P0 | Add post-deploy smoke checks. | CI/Railway smoke after deploy for API and optionally frontend health. | Full browser E2E. | Failed smoke fails deployment job. |
| SAC-005 | P1 | Wire per-business RBAC. | Use `BusinessMembership.role` in authorization context where business-scoped permissions require it. | Full staff invitation lifecycle. | Cross-business/membership role tests. |
| UX-SVC | P1 | Add owner services screen. | Frontend CRUD for services using existing backend APIs. | Billing/plan enforcement. | Vitest/component and BFF/action tests. |
| UX-HOURS | P1 | Add owner hours and closure screens. | Working hours, availability exceptions, recurring staff blocks. | Calendar drag/drop UI. | Frontend tests plus backend API contract check. |
| PUBLIC-LINK | P1 | Add customer booking management link. | Signed public cancel/reschedule URL in SMS flow. | Anonymous account creation. | Token tamper/expiry tests and cancel/reschedule tests. |
| METRICS-OWNER | P2 | Add owner metrics API and dashboard. | Tenant-safe metrics for bookings/cancellations/conversion where data exists. | Revenue analytics until billing exists. | API and frontend tests. |
| EXPORT-CSV | P2 | Add CSV export. | Owner booking/client export with tenant/business scoping. | Scheduled reports. | API tests for auth, scoping, and CSV content. |
| SMS-I18N | P2 | Add SMS localization boundary. | `business.language`/message renderer or equivalent safe locale approach. | User-editable templates unless placeholder validation is included. | Unit tests for locale selection and safe placeholders. |
| TELEPHONY-OPS | P2 | Add phone number inventory and assignment if still required. | `BusinessPhoneNumber`, assignment API, telephony status, dashboard card. | BYO phone porting. | Migration/model/API/frontend tests. |
| SAC-009 | P2 | Implement staff invitation lifecycle safely. | Verify production schema state, add guarded migration/routes/email flow. | Staff self-service calendar UI. | Migration idempotency and invite accept/revoke tests. |
| E2E-001 | P2 | Add browser E2E for critical dashboard/demo paths. | Login, bookings, demo read-only, basic dashboard navigation. | Large visual regression suite. | CI-compatible E2E job or documented local gate. |
| CAL-OAUTH | P3 | Implement real calendar connection flow. | Provider OAuth/setup and read-only busy import if product direction confirms it. | External calendar as booking source of truth. | ADR-compatible tests and privacy checks. |
| BILLING-001 | P3 | Add billing/subscription model. | Stripe customer/subscription/price linkage and webhooks. | Deposit payment links unless explicitly prioritized. | Webhook idempotency and plan state tests. |

## Risk Register

| Risk | Mitigation |
|---|---|
| Production deploy can succeed while API is unhealthy. | OPS-001 and TEST-001 before relying on production demo. |
| Business-scoped roles are stored but not enforced. | Complete SAC-005 before staff access expansion. |
| Public customer links can become account-bypass vectors. | Use signed, scoped, expiring tokens and avoid exposing broader customer data. |
| User-editable SMS templates can inject unsafe content or lose placeholders. | Add placeholder validation before template editing. |
| Calendar sync can become a competing source of truth. | Keep ADR 0002/0005/0006 constraints: local bookings remain authoritative. |

## Validation Commands

Choose the smallest relevant set for the task:

```bash
make validate
make policy-guards
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
cd frontend && pnpm api:check
```
