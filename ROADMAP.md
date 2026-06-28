# Roadmap — VoxSlot

This file tracks future work and active execution order. Completed historical
implementation detail belongs in Git history, ADRs, archived audits, or
[`docs/project/current-state.md`](docs/project/current-state.md).

Detailed task-level backlog: [`docs/project/implementation-backlog.md`](docs/project/implementation-backlog.md).

## Product Goal

Build a mini SaaS for appointment-based businesses that miss calls while staff
are busy. The product should answer calls, guide customers through booking or
transfer, keep appointments in PostgreSQL, send SMS updates, and give owners an
operational dashboard.

## Current Baseline

The core backend, local IVR demo, Twilio/SMS boundaries, worker infrastructure,
and initial owner dashboard are implemented. The project is not production-ready
as a general SaaS. See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and
[`docs/project/current-state.md`](docs/project/current-state.md).

## Next Recommended Execution Order

1. Verify and repair production Railway health if the API is still returning
   errors.
2. Add a visible `/demo` path from the landing page if the public demo is meant
   to be discoverable.
3. Complete per-business RBAC cutover from `User.role` to
   `BusinessMembership.role` where required.
4. Add production post-deploy smoke checks for API/frontend health.
5. Build missing owner dashboard configuration screens: services, working
   hours, recurring blocks, availability exceptions, clients, calendar setup,
   and telephony status.
6. Add public customer booking management links for cancel/reschedule.
7. Add owner metrics API and CSV export.
8. Add SMS localization and template policy before user-editable templates.
9. Decide and implement telephony inventory: `BusinessPhoneNumber`, operator
   assignment API, telephony status, and frontend status card.
10. Implement staff invitation/access lifecycle after verifying production
    schema state for the historical SAC-009 stub.
11. Add browser-driven E2E coverage for login, dashboard, booking management,
    and demo read-only behavior.
12. Defer billing/subscription enforcement until pilot operations are stable.

## Strategic Tracks

| Track | Objective | Current blocker |
|---|---|---|
| Production confidence | Make Railway health, smoke tests, rollback, backup, and observability reliable. | Post-deploy smoke and active production health verification. |
| Owner operations | Let owners configure services, hours, staff, closures, recurring blocks, clients, and metrics without API tools. | Missing dashboard screens and some API aggregation endpoints. |
| Customer self-service | Let customers manage bookings without another phone call. | Public signed booking-management link not implemented. |
| Staff access | Move from tenant-level user role checks toward per-business staff/admin ownership. | `BusinessMembership.role` not wired into runtime auth. |
| Telephony operations | Manage assigned phone numbers and telephony state cleanly. | `BusinessPhoneNumber` and operator assignment flow not on `main`. |
| Commercial SaaS | Add plans, billing, phone provisioning, and subscription enforcement. | Not a near-term blocker for the local/pilot demo. |

## References

- Active status: [`PROJECT_STATUS.md`](PROJECT_STATUS.md)
- Active debt: [`TECH_DEBT.md`](TECH_DEBT.md)
- Current implementation snapshot: [`docs/project/current-state.md`](docs/project/current-state.md)
- Executable backlog: [`docs/project/implementation-backlog.md`](docs/project/implementation-backlog.md)
- Staff/calendar specification: [`docs/specs/staff-access-and-calendar.md`](docs/specs/staff-access-and-calendar.md)
- Archived recovery audits: [`docs/archive/README.md`](docs/archive/README.md)
