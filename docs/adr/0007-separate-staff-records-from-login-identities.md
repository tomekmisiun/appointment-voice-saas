# ADR 0007: Separate Staff Records from Login Identities

- **Status:** Accepted
- **Date:** 2026-06-24
- **Roadmap:** SAC-001 through SAC-014

## Context

The current repository already separates `Staff` and `User`, but only by
absence of a relationship. `Staff` is a tenant/business scheduling resource
(`app/models/staff.py`); `User` owns `tenant_id` and a tenant-wide role
(`app/models/user.py`). There is no membership model. The helper named
`tenant_membership_service.py` validates the direct user/tenant relationship
rather than persisted membership.

This prevents optional staff access from being represented safely. Reusing
`User` as an employee would require login credentials for every scheduled
person. Adding `user_id` directly to `Staff` would still leave role/status and
multi-business access on the wrong entity. Renaming the current `user` role to
`staff` would also be unsafe because authenticated read endpoints currently
list all staff and bookings (`app/api/routes/staff.py`,
`app/api/routes/bookings.py`).

## Decision

1. Keep `Staff` as the physical employee business record for the initial
   implementation. “Employee” is product terminology; avoid a table rename
   that adds migration risk without changing semantics.
2. Make `User` the login identity and account-security record. In the target
   model it does not own a business role.
3. Add a persisted business membership that links user, tenant, and business,
   and stores `owner|admin|staff` plus access status.
4. Link a staff membership to one `Staff` record. Staff can exist with no
   membership; owner/admin membership can exist without staff linkage.
5. Enforce at most one membership per user/business and at most one active
   membership per staff/business. A staff membership requires the staff link.
6. Resolve authorization from an active membership on every backend request.
   Staff self-service derives staff ID from membership; it never trusts a
   client-selected staff ID.
7. Revoke/suspend membership and invalidate sessions without deleting staff,
   users, bookings, or audit history.
8. Preserve workspace + email + password login during the first migration.
   Global identity consolidation is a later decision because current email
   uniqueness is tenant-scoped and duplicate emails may have different hashes.

## Alternatives considered

### Add nullable `user_id` and `role` to `Staff`

Rejected. Owners/admins need access even when they are not scheduled staff,
and access status/role lifecycle is not an employee attribute.

### Require a `User` for every staff record

Rejected. It violates the business requirement that non-login employees still
participate in services, schedules, bookings, and calendars.

### Keep role and tenant directly on `User`

Rejected as the target. It cannot represent per-business access, optional
employee linkage, or different roles in different workspaces. It remains only
as a staged migration compatibility mechanism.

### Rename role `user` to `staff`

Rejected. Current `user` access is broader than target staff self-scope, and no
employee link exists from which to enforce ownership.

## Consequences

**Positive:** employee history is independent of credentials; access can be
revoked safely; roles become business-scoped; owner/admin/staff policy can be
tested explicitly; future multi-workspace identities become possible.

**Negative:** auth context, JWT/session invalidation, services, workers, BFF,
and every protected route need staged migration. Existing users need membership
backfill. Duplicate cross-tenant identities cannot be merged automatically.

**Required follow-ups:** SAC-003 through SAC-014 in the executable staff-access
roadmap. No runtime change is made by this ADR.

