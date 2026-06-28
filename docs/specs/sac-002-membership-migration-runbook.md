# SAC-002: Membership Expand/Backfill/Contract Migration Runbook

- **Status:** Planned
- **Backlog:** [`docs/project/implementation-backlog.md`](../project/implementation-backlog.md)
- **Architecture:** [`docs/specs/staff-access-and-calendar.md`](staff-access-and-calendar.md)
  §"Migration and backfill strategy" and §`business_memberships` (binding target
  schema; not redefined here)
- **Decision:** [ADR 0007](../adr/0007-separate-staff-records-from-login-identities.md)
- **Evidence:** [`docs/operations/runbooks/membership-data-preflight.md`](../operations/runbooks/membership-data-preflight.md),
  `app/ops/membership_preflight.py` (SAC-001)
- **Out of scope:** Alembic migrations and runtime code. This is the sequencing
  plan that SAC-003 (schema), SAC-004 (backfill), and SAC-005 (RBAC cutover)
  implement.

## Objective

Define a reversible, evidence-driven sequence for introducing
`business_memberships` and making it authoritative for authorization, so that
every legacy user/role state has a documented forward action and a documented
rollback, and no step can silently broaden access or merge identities.

## Phase plan

| Phase | Task | Behavior change? | Legacy columns | Rollback |
|-------|------|-------------------|----------------|----------|
| Expand | SAC-003 | None | `User.tenant_id`/`role` still authoritative | `alembic downgrade` — table is empty/unread |
| Backfill | SAC-004 | None (writes only) | Still authoritative | Delete backfilled rows; legacy auth unaffected |
| Transition/cutover | SAC-005 | Yes — membership becomes authoritative | Kept and actively mirrored (see "Dual-read / dual-enforce" step 6) | Flip feature flag back to legacy; safe as long as mirroring held |
| Contract | separate, later, separately-approved branch (not in this roadmap's MVP scope) | Yes | Removed | Not reversible without restore — requires its own backup/rollback plan per `.ai-rules/database.md` |

Each phase is its own PR/branch per `.ai-rules/incremental-work.md`. A phase
does not start until the previous phase's acceptance criteria are verified in
the target environment.

### Entry/exit criteria

- **SAC-003 exit:** migration applies cleanly upgrade/downgrade; constraints
  from the target schema (`docs/specs/staff-access-and-calendar.md`
  §`business_memberships`) are enforced; zero rows expected (table is new).
- **SAC-004 exit:** every tenant from the SAC-001 report is accounted for in
  one of the categories below; verification counts (below) reconcile; rerun
  is a no-op. `tenants_pending_owner_confirmation` reaching `0` is **not**
  part of SAC-004's exit — that is an ongoing operator task tracked
  separately, since it depends on humans confirming real-world ownership,
  not on backfill code.
- **SAC-005 exit:** dual-read mismatch rate is zero (or every mismatch is
  triaged) for the observation window defined below; full RBAC matrix in
  `docs/specs/staff-access-and-calendar.md` §"RBAC model" passes; cutover flag
  flipped.

## Owner/admin inference rules

These rules consume the per-tenant classification already produced by SAC-001
(`app.ops.membership_preflight.TenantResolution`). They are deliberately
conservative: **never infer across the `duplicate_email_across_tenants`
reason, and never auto-link by email.** This is the binding security
constraint from the SAC-002 roadmap card.

**SAC-004 does not auto-promote anyone to `owner`.** The architecture spec's
bar is "the deterministic tenant creator when audit evidence identifies it";
today's `tenant.created` audit log only records `source="self_signup"` at
the tenant level — it does not store *which user* was created. "Exactly one
admin exists right now" is not creator identity: that admin could have been
added after the original signup admin was demoted, deactivated, or replaced,
with nothing in the data distinguishing that case from the real signup
admin still being the sole admin. Treating tenant-level signup evidence as
user-level creator proof would risk auto-granting `owner` (transfer, billing
— see the RBAC model table) to the wrong person on exactly the kind of
tenant this runbook is supposed to protect. So, for every tenant with at
least one admin and one business, regardless of business/admin counts,
self-signup status, or duplicate-email status: **create `admin` (never
`owner`) for every admin/platform_admin user, scoped to every business the
tenant has, and let an operator confirm and promote exactly one membership
per business to `owner`.** This is true even for a tenant with only one
business and one admin — the single admin still only gets `admin` until
confirmed.

| SAC-001 tenant state | Forward action (SAC-004 backfill) | Confidence |
|---|---|---|
| 1. `no_admin` (regardless of any other reason also present) | Create no `owner`/`admin` membership (there is no admin-role user to create one for). Tenant is recorded as `unresolved: no_admin` in the backfill report. | None |
| 2. `no_business` (regardless of any other reason also present) | Create no membership (nothing to scope it to). Tenant is recorded as `unresolved: no_business`. | None |
| 3. Everything else with at least one admin and one business — any combination of "safe" counts, `multiple_businesses`, `multiple_admins`, `duplicate_email_across_tenants`, with or without self-signup evidence, with `no_admin`/`no_business` absent | Create one `admin` membership per (admin, business) pair for that tenant. No membership is auto-promoted to `owner` under any combination of reasons. An operator confirms and promotes exactly one membership per business to `owner`. | Low — flag for operator review |

### Future automatic owner inference (explicitly out of SAC-004's initial scope)

If auto-`owner` for self-signup tenants is wanted later, it requires a
*preceding*, separately reviewed change — not an assumption baked into
SAC-004:

1. `app/services/tenant_service.py::signup_tenant` starts recording the
   created admin's `user_id` as `target_user_id` on the `tenant.created`
   audit log row.
2. Only after that exists, the rule becomes: a tenant auto-promotes to
   `owner` if and only if its `tenant.created` row has `source="self_signup"`
   **and** `target_user_id` matches a user who **currently** has an active
   admin/platform_admin membership in that tenant — an exact identity match,
   not a coincidental count of one. If that exact user is no longer an
   admin, fall through to manual resolution (row 3) instead of guessing.

Operator resolution for any tenant in row 3: after
backfill, an operator promotes exactly one membership per business to `owner`
through a documented one-off SQL change (not an automated heuristic), logged
as an `AuditLog` row with a `source="sac004_manual_resolution"` value. This
promotion alone does **not** call `increment_user_token_version()` — see
"Session invalidation" below for why pre-cutover membership changes do not
invalidate sessions.

## Forward/rollback treatment by legacy state

This table satisfies the SAC-002 acceptance criterion that *"every legacy
role/state has forward and rollback treatment."*

| Legacy state | Forward (SAC-004) | Rollback |
|---|---|---|
| `role="admin"` / `"platform_admin"`, resolvable per the table above | Membership row(s) created per the inference rules | Delete the created membership row(s); legacy `role` column is untouched, so no functional change |
| `role="user"` (no admin rights) | **No membership row created.** Recorded as `unresolved_user` in the backfill report; out of scope until an explicit invitation (SAC-009–011) or operator decision links the account to a `staff` membership with a real `staff_id`. See note below — this is a deliberate, narrower reading than the architecture spec's prose. | N/A — no row created |
| Existing `Staff` rows | Not linked to any membership by SAC-004 (linking is invitation-driven per the architecture spec, never automatic-by-name/contact-match) | N/A — no row created |
| `Staff` rows flagged `orphan_staff_references` by SAC-001 | Excluded from any membership linkage until the underlying tenant/business mismatch is fixed as a one-off data correction (tracked separately, not part of this migration) | N/A — excluded, no row created |
| `platform_admin` acting as a tenant's de facto operator (for example, the seeded default tenant) | Treated like any other tenant admin for *that tenant's* membership purposes; platform-wide `platform_admin` capability is untouched and remains separate from business membership (see the "Platform administration" row in the RBAC model table) | Delete the tenant-scoped membership row only; platform role is unaffected |
| Tenants already past `multiple_businesses`/`multiple_admins` resolution by an operator | Resulting memberships are treated as normal data going forward; no special rollback path beyond the generic one | Delete affected rows; same as any membership |

**Reconciling `role="user"` with the architecture spec:**
`docs/specs/staff-access-and-calendar.md` §"Migration and backfill strategy"
step 3 says to map `user` to "a suspended/unlinked legacy membership," which
reads as if every plain user gets a placeholder row. The same document's
`business_memberships` constraint list states unconditionally that "staff
role requires `staff_id`" — there is no fourth role value for an unlinked
placeholder, and weakening that constraint to admit `staff_id=NULL` (for
example by scoping it to `status="active"` only) was considered and rejected:
it would quietly carve an exception into a documented authorization
invariant without that change going through its own review. This runbook
resolves the conflict in favor of the **constraint, not the prose**: no
membership row is created for unlinked plain users at backfill time. This is
also the more conservative, fail-closed choice consistent with SAC-004's own
security considerations ("fail closed on ambiguity"). If a real placeholder
row turns out to be needed later (for example, to make a reconciliation
count balance), that requires its own small spec amendment with an explicit
schema answer (a new role/status value, or a relaxed constraint reviewed on
its own terms) — not a default assumed here.

## Verification counts (SAC-004 idempotency contract)

The backfill command must log, per run:

- `tenants_total`, `tenants_unresolved_no_admin`, `tenants_unresolved_no_business`
  (these three reuse `MembershipPreflightReport`'s own categories directly,
  comparable run-over-run and against the SAC-001 report taken immediately
  before the run).
- `tenants_pending_owner_confirmation` — **SAC-004's own bucket, deliberately
  not the same as SAC-001's `safe_tenant_ids`.** Per the owner-inference
  rules above, no tenant gets an auto-confirmed `owner` during backfill, so
  this count includes every tenant with at least one admin and one
  business — including ones SAC-001 reported as "safe." Do not reuse or
  rename this to `tenants_safe`/`tenants_needing_manual_resolution` as if it
  mirrored SAC-001's classification; SAC-001's "safe" only describes
  business/admin/email counts, not whether an `owner` has been confirmed.
  This count only goes to `0` for a tenant once an operator's manual
  resolution step (below) has promoted exactly one membership per business
  to `owner` — it does not shrink on its own as part of any backfill run.
- `memberships_created`, `memberships_skipped_existing` (already created by a
  prior run — this is what makes rerun safe).
- `users_total` — from `app.ops.membership_preflight.count_users_per_tenant`,
  summed across all tenants, queried fresh each run (not carried over).
- `users_with_membership` — `COUNT(DISTINCT user_id)` over the
  `business_memberships` table's **current state after this run**, not just
  rows created by this run. This is what makes it rerun-stable: on a second
  run, `memberships_created` is `0` but `users_with_membership` is unchanged
  from the first run's result, because it is a query against the table, not
  a per-run delta.
- `users_unresolved` — `users_total - users_with_membership`, decomposed for
  visibility into: users in `no_admin` tenants, users in `no_business`
  tenants, and plain `role="user"` rows in otherwise-resolved tenants (the
  reconciliation-note case above). Every one of these three sub-buckets is
  expected to be non-zero in a real dataset and is **not** a bug — only an
  *unexplained* change in `users_unresolved` between runs against the same
  data is.
- **Required invariant, verified by query every run:**
  `users_with_membership + users_unresolved == users_total`. This is what
  satisfies SAC-004's own acceptance criterion that "every current user is
  accounted for" — every user is in exactly one of the two buckets, computed
  from current state, not assumed from this run's write counts.
- A rerun against the same database MUST produce `memberships_created == 0`,
  `memberships_skipped_existing` equal to the previous run's
  `memberships_created` total, and `users_with_membership`/`users_unresolved`
  identical to the previous run. Enforce the membership half with a unique
  constraint on `(business_id, user_id)` from the SAC-003 schema, not just
  application logic — the backfill upserts against that constraint rather
  than checking-then-inserting.

## Dual-read / dual-enforce (SAC-005 cutover)

1. Add a settings flag, e.g. `membership_authorization_enabled: bool = False`
   (same pattern as `legacy_routes_enabled` / `worker_maintenance_enabled` in
   `app/core/config.py`), defaulting to `False` in every environment.
2. While the flag is `False`, requests continue to authorize from
   `User.tenant_id`/`role` exactly as today. The new
   `AuthorizationContext` (per the architecture spec's RBAC section) is
   computed in parallel and *compared* to the legacy decision for every
   request that hits a route already migrated to call both paths, without
   changing the response.
3. Log a mismatch metric (count, not request payloads — no PII) whenever the
   two decisions disagree, tagged by route and mismatch direction (legacy
   allowed/new denied vs. legacy denied/new allowed). The known cause of
   "legacy allowed/new denied" mismatches is exactly the ADR 0007 finding that
   today's `role="user"` reads are broader than the target staff self-scope —
   expect this direction to be non-zero and reviewed, not silently flipped.
4. Only flip `membership_authorization_enabled=True` in an environment after
   the mismatch count has been reviewed for at least one full business-hours
   observation window (operator judgment per environment; this runbook does
   not hardcode a duration) and every mismatch is either accepted as an
   intentional access-narrowing (documented) or fixed.
5. The flip itself executes the session cutover below — it is the "no
   pre-membership session survives role migration" moment required by
   `docs/specs/staff-access-and-calendar.md` §"Migration and backfill
   strategy" step 6.
6. **After the flip, every membership mutation (revoke, suspend, role
   change, invitation acceptance creating a new membership) continues to be
   mirrored to the legacy `User.tenant_id`/`role`/`is_active` columns.** This
   extends SAC-004's own "dual-representation consistency checks" past
   backfill, through the cutover, until the contract phase removes the
   legacy columns entirely. Without this, the columns the rollback below
   depends on would go stale the first time someone is revoked or
   re-roled after cutover, and flipping back would silently restore their
   old access.
7. Rollback is flipping the flag back to `False`, **and is only a
   no-further-action rollback while step 6's mirroring has held** — this is
   the "Application rollback" case in `docs/operations/runbooks/migration-rollback.md`
   (schema-compatible, behavior-only fix). If mirroring is ever found to be
   incomplete for some user (bug, race, or a manual DB fix that bypassed the
   service layer), reconcile that user's legacy columns to match their
   membership state *before* flipping back, or treat it as a forward-fix /
   restore-from-backup situation per `docs/operations/runbooks/migration-rollback.md` instead of
   assuming the flag alone is sufficient. Rolling back does **not** undo the
   forced reauthentication from step 5 — that is a one-time, intentionally
   irreversible safety step, not a rollback target.

## Session/token invalidation

Reuse the existing mechanism — no new primitive needed:
`app/services/user_service.py::increment_user_token_version()` bumps
`User.token_version`; already-issued access/refresh tokens fail the check in
`app/api/dependencies/auth.py:63` and `app/services/auth_service.py:158` on
next use.

- **Backfill (SAC-004) does not call this.** Creating a membership row for a
  user whose effective access does not change yet (legacy auth is still
  authoritative) must not log anyone out.
- **Manual resolution before cutover** (an operator promoting one of several
  backfilled `admin` memberships to `owner`, or correcting a wrong backfill
  row) **does not** call this either, by itself. Legacy `User.tenant_id`/
  `role` are still authoritative at this point and are untouched by a
  membership-only change, so the user's actual access has not changed — an
  explicit bump here would be an avoidable logout with no security benefit.
  If the *same* operator action also corrects a legacy column (for example,
  the legacy `role` was itself wrong), use the existing
  `update_user()`/`deactivate_user()` path for that — `token_version`
  already increments as a side effect of the role/`is_active` change those
  functions make, so there is no separate invalidation step to add.
- **Cutover (SAC-005)**, per `docs/specs/staff-access-and-calendar.md`
  §"Migration and backfill strategy" step 6, increments `token_version` for
  every user in scope of the flip (all users, if the flag is global; the
  affected tenants' users, if rolled out per-tenant), forcing
  reauthentication. This is intentional, one-time, and disruptive by design:
  even though the dual-read window above already validated decision parity
  for normal traffic, forced reauth is the defense-in-depth backstop against
  any mismatch dual-read did not observe. It must run as a single deliberate,
  communicated maintenance step at the moment of the flip — not repeated on
  every subsequent membership change.
- **Post-cutover membership mutations call `increment_user_token_version()`
  directly and explicitly — do not rely on the legacy mirror write for
  this.** The legacy `role` column is coarser than membership `role`: both
  `owner` and `admin` mirror to legacy `role="admin"`, so an `owner`→`admin`
  demotion (or `active`→`suspended`, with `is_active` otherwise unchanged if
  mirrored differently) can leave the mirrored legacy columns *unchanged*,
  which means `update_user()`'s own change-detection (`role != user.role`)
  sees no diff and skips its bump. Once membership is authoritative
  (post-cutover), every membership role/status change invalidates that
  user's sessions on its own terms, independent of whether the legacy
  mirror happened to change too.

## Rollback checkpoints

| After | Rollback action | Data risk |
|---|---|---|
| SAC-003 merged, before any backfill ran | `alembic downgrade` to drop the table | None — table is empty |
| SAC-004 ran in an environment | Delete rows created by that backfill run (or truncate the table if no manual resolution has happened yet); legacy auth is untouched | None — membership is not yet read by any auth path |
| SAC-005 flag flipped to `True` | Flip back to `False` | Low *while* every post-cutover membership mutation has been mirrored to legacy columns (dual-read step 6); if mirroring gaps are found, reconcile affected users' legacy columns first — see dual-read step 7 |
| Contract (legacy column removal) | Out of scope for this runbook; requires its own backup, since this step is destructive | High — restore-from-backup is the only path back; see `docs/operations/runbooks/migration-rollback.md` §"Database Rollback Policy" |

## Backup/restore rehearsal

Before running SAC-004 backfill against any real (non-empty) database:

```bash
make db-backup         # wraps scripts/db_backup.sh
make db-restore-check  # wraps scripts/db_restore_rehearsal.sh + app/ops/restore_verification.py
```

The rehearsal must succeed — restore completes and
`build_restore_verification_sql()` checks pass — before the backfill runs.
SAC-003's definition of done includes adding `business_memberships` to
`CORE_RESTORE_TABLES` in `app/ops/restore_verification.py` so this check
covers the new table from day one.

## Dry-run examples (anonymized fixture states)

These mirror `tests/test_ops_membership_preflight.py` fixtures and double as
the "dry-run examples against anonymized fixture states" required by this
task's acceptance criteria — no real data, illustrative only.

1. **Self-signup tenant (evidence is not yet enough to auto-act on).**
   `tenant_id=42`, 1 business, 1 admin user (`user_id=101`), a
   `tenant.created` audit log row with `source="self_signup"`, 1 plain
   `role="user"` row (`user_id=102`). Even with this evidence, SAC-004 creates
   `business_membership(tenant_id=42, business_id=7, user_id=101,
   role="admin", status="active")` — **not** `owner` (see "Future automatic
   owner inference" above for why signup evidence alone isn't enough yet) —
   and creates **no** row for `user_id=102` (recorded as `unresolved_user`,
   per the reconciliation note above). An operator confirms and promotes
   `user_id=101` to `owner`. Rollback: delete the one membership row.
2. **Safe counts, no signup evidence.** `tenant_id=47`, 1 business, 1 admin
   user (`user_id=401`), no `tenant.created` audit log row (for example, the
   tenant predates the self-signup feature, or was created via
   `POST /admin/tenants`). Same outcome as example 1: SAC-004 creates
   `business_membership(tenant_id=47, business_id=9, user_id=401,
   role="admin", status="active")`. Tenant counts toward
   `tenants_pending_owner_confirmation` even though it has only one admin.
   An operator confirms and promotes `user_id=401` to `owner`.
3. **Multiple admins.** `tenant_id=43`, 1 business, 2 admin users
   (`user_id=201`, `user_id=202`). SAC-004 creates two `admin` memberships,
   no `owner`. Tenant counts toward `tenants_pending_owner_confirmation`.
   An operator later promotes
   `user_id=201` to `owner`; no session invalidation happens at that point
   (legacy auth is still authoritative — see "Session/token invalidation").
4. **No admin.** `tenant_id=44`, 1 business, 0 admin users, 1 plain
   `role="user"` row (`user_id=301`). SAC-004 creates zero memberships;
   tenant is recorded as `unresolved_no_admin`. No rollback needed because
   nothing was written.
5. **Cross-tenant duplicate email.** `tenant_id=45` and `tenant_id=46` both
   have an admin with the same (normalized) email, and neither has
   self-signup evidence. Even though each tenant has exactly 1 business and
   1 admin, the shared email alone makes both tenants `manual_resolution`
   (matching `app.ops.membership_preflight`'s own classification — though per
   table row 3 above, they would have needed operator confirmation anyway,
   duplicate email or not). SAC-004 creates an `admin` membership (not `owner`) for
   each tenant's admin user; an operator reviews both independently and
   promotes each to `owner` once confirmed. The email is never used to merge
   the two memberships or the two `User` rows.

## Acceptance criteria

1. Every SAC-001 tenant-state category above has both a forward action and a
   rollback action documented (this runbook).
2. No rule auto-links across tenants by email, and no rule auto-promotes
   anyone to `owner`; every owner assignment requires explicit operator
   confirmation (table above).
3. Destructive contract (legacy column removal) is explicitly deferred to a
   separately approved branch, never bundled with backfill or cutover.
4. Backfill (SAC-004) and manual resolution invalidate sessions only for
   users whose effective access actually changes; the one blanket bump is
   the deliberate, one-time cutover step (SAC-005) required by the
   architecture spec, not a routine backfill action.
5. A backup/restore rehearsal precedes backfill execution in any non-empty
   environment.

## Definition of done

- This document is reviewed and accepted before SAC-003 implementation
  starts (read-only Reviewer covers sequencing/security/correctness since
  there is no application code in this branch).
- No `make validate` run is required — no application code, migrations, or
  AI workflow files changed (`.ai-rules/agent-orchestration.md` §6 docs-only
  row).
