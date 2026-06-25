"""SAC-004: idempotent membership backfill.

Creates `business_memberships` rows for every tenant that has at least one
admin/platform_admin user and at least one business, per the owner/admin
inference rules in
docs/specs/sac-002-membership-migration-runbook.md#owneradmin-inference-rules.

Deliberately conservative, matching that runbook:
- Never auto-promotes anyone to `owner` -- every admin/platform_admin user
  gets an `admin` membership for every business of their tenant; an operator
  confirms and promotes exactly one membership per business to `owner`.
- Never auto-links across tenants by email.
- Never creates a placeholder row for plain `role="user"` accounts -- the
  SAC-003 schema's `staff` role requires a real `staff_id`, and linking is
  invitation-driven (SAC-009-011), not automatic.
- Writes only: `User.tenant_id`/`role` remain authoritative until the SAC-005
  cutover, so this never calls `increment_user_token_version()`.
- Safe to rerun: each insert is attempted against the unique
  `(business_id, user_id)` constraint from SAC-003 and skipped on conflict,
  not checked-then-inserted.

Run with:
    docker compose run --rm api python -m app.ops.membership_backfill
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models.business import Business
from app.models.business_membership import (
    BusinessMembership,
    MembershipRole,
    MembershipStatus,
)
from app.models.user import User
from app.ops.membership_preflight import (
    ADMIN_ROLES,
    REASON_NO_ADMIN,
    REASON_NO_BUSINESS,
    TenantResolution,
    build_membership_preflight_report,
    count_users_per_tenant,
)

# Bounds locks-per-transaction for one backfill commit, independent of how
# many (admin, business) pairs any single tenant happens to own.
_BACKFILL_COMMIT_CHUNK_SIZE = 200


def tenant_eligible_for_backfill(resolution: TenantResolution) -> bool:
    """At least one admin and one business -- regardless of any other
    reason (multiple_businesses, multiple_admins, duplicate_email_across_tenants)
    also present. See the SAC-002 runbook's owner/admin inference table."""
    return (
        REASON_NO_ADMIN not in resolution.reasons
        and REASON_NO_BUSINESS not in resolution.reasons
    )


def list_business_ids_by_tenant(
    db: Session, tenant_ids: tuple[int, ...]
) -> dict[int, tuple[int, ...]]:
    if not tenant_ids:
        return {}

    rows = (
        db.query(Business.tenant_id, Business.id)
        .filter(Business.tenant_id.in_(tenant_ids))
        .order_by(Business.tenant_id, Business.id)
        .all()
    )
    grouped: dict[int, list[int]] = {}
    for tenant_id, business_id in rows:
        grouped.setdefault(tenant_id, []).append(business_id)

    return {tenant_id: tuple(ids) for tenant_id, ids in grouped.items()}


def _tenant_ids_pending_owner_confirmation(
    db: Session,
    *,
    tenant_ids: tuple[int, ...],
    business_ids_by_tenant: dict[int, tuple[int, ...]],
) -> tuple[int, ...]:
    """A tenant stops being "pending" only once an operator has promoted
    exactly one membership per business to `owner` -- per the SAC-002
    runbook, this does not shrink on its own as part of any backfill run,
    so it must check for existing active `owner` rows, not just
    admin/business eligibility.
    """
    business_ids = tuple(
        business_id
        for ids in business_ids_by_tenant.values()
        for business_id in ids
    )
    owned_business_ids: set[int] = set()
    if business_ids:
        rows = (
            db.query(BusinessMembership.business_id)
            .filter(BusinessMembership.business_id.in_(business_ids))
            .filter(BusinessMembership.role == MembershipRole.OWNER)
            .filter(BusinessMembership.status == MembershipStatus.ACTIVE)
            .distinct()
            .all()
        )
        owned_business_ids = {business_id for (business_id,) in rows}

    return tuple(
        tenant_id
        for tenant_id in tenant_ids
        if not all(
            business_id in owned_business_ids
            for business_id in business_ids_by_tenant.get(tenant_id, ())
        )
    )


def _stage_admin_membership(
    db: Session, *, tenant_id: int, business_id: int, user_id: int
) -> bool:
    """Stages one membership insert inside a SAVEPOINT and reports whether it
    would be new. Returns True if staged, False if one already existed (the
    unique-constraint conflict was caught and rolled back to the savepoint).

    Does not commit -- the caller commits once per tenant. A backfill can
    touch every tenant in the database, so locks must not accumulate across
    an entire run in one transaction (that previously caused a Postgres
    "out of shared memory" failure under a large dataset), but batching
    every tenant's own (small) set of inserts into one commit avoids paying
    a network round trip per row.
    """
    try:
        with db.begin_nested():
            db.add(
                BusinessMembership(
                    tenant_id=tenant_id,
                    business_id=business_id,
                    user_id=user_id,
                    role=MembershipRole.ADMIN,
                    status=MembershipStatus.ACTIVE,
                )
            )
            db.flush()
    except IntegrityError:
        return False

    return True


@dataclass(frozen=True)
class MembershipBackfillReport:
    generated_at: datetime
    tenants_total: int
    tenants_unresolved_no_admin: tuple[int, ...]
    tenants_unresolved_no_business: tuple[int, ...]
    tenants_pending_owner_confirmation: tuple[int, ...]
    memberships_created: int
    memberships_skipped_existing: int
    users_total: int
    users_with_membership: int
    users_unresolved: int
    users_unresolved_no_admin_tenant: int
    users_unresolved_no_business_tenant: int
    users_unresolved_plain_role: int


def run_membership_backfill(
    db: Session, *, tenant_ids: tuple[int, ...] | None = None
) -> MembershipBackfillReport:
    """`tenant_ids`, if given, restricts which tenants are written to --
    for a staged per-tenant rollout, or to scope a single backfill call in
    a test. It does not affect the verification counts below: those are
    deliberately always global per the SAC-002 runbook (`users_total`,
    `users_with_membership`, etc. are invariants over the whole database,
    not per-call deltas), and they are read-only aggregate queries, not the
    locking concern `tenant_ids` exists to bound.
    """
    report = build_membership_preflight_report(db)

    admin_user_ids_by_tenant: dict[int, list[int]] = {}
    for row in report.admin_users:
        admin_user_ids_by_tenant.setdefault(row.tenant_id, []).append(row.user_id)

    # Global eligibility drives every verification count below (per the
    # docstring above, those never narrow to `tenant_ids`). The write loop
    # below additionally narrows to `write_eligible_tenant_ids`.
    globally_eligible_tenant_ids = tuple(
        resolution.tenant_id
        for resolution in report.tenant_resolutions
        if tenant_eligible_for_backfill(resolution)
    )
    write_eligible_tenant_ids = tuple(
        tenant_id
        for tenant_id in globally_eligible_tenant_ids
        if tenant_ids is None or tenant_id in tenant_ids
    )
    business_ids_by_tenant = list_business_ids_by_tenant(db, globally_eligible_tenant_ids)

    memberships_created = 0
    memberships_skipped_existing = 0
    staged_since_commit = 0

    for tenant_id in write_eligible_tenant_ids:
        for user_id in admin_user_ids_by_tenant.get(tenant_id, []):
            for business_id in business_ids_by_tenant.get(tenant_id, []):
                created = _stage_admin_membership(
                    db, tenant_id=tenant_id, business_id=business_id, user_id=user_id
                )
                if created:
                    memberships_created += 1
                else:
                    memberships_skipped_existing += 1

                # Commit in fixed-size chunks, independent of tenant
                # boundaries: a single tenant can still own an unbounded
                # number of (admin, business) pairs, and Postgres's lock
                # table is shared across every concurrent connection on the
                # server, so even a "per tenant" transaction can be the one
                # that tips a shared budget over the edge. A crashed run is
                # resumable from the next chunk rather than losing all
                # prior work.
                staged_since_commit += 1
                if staged_since_commit >= _BACKFILL_COMMIT_CHUNK_SIZE:
                    db.commit()
                    staged_since_commit = 0

    if staged_since_commit > 0:
        db.commit()

    tenants_unresolved_no_admin = tuple(
        resolution.tenant_id
        for resolution in report.tenant_resolutions
        if REASON_NO_ADMIN in resolution.reasons
    )
    tenants_unresolved_no_business = tuple(
        resolution.tenant_id
        for resolution in report.tenant_resolutions
        if REASON_NO_BUSINESS in resolution.reasons
    )

    # Queried fresh every run, not carried over from this run's write counts
    # -- see the SAC-002 runbook's "Verification counts" section.
    users_total = sum(count_users_per_tenant(db).values())
    users_with_membership = (
        db.query(func.count(func.distinct(BusinessMembership.user_id))).scalar() or 0
    )
    users_unresolved = users_total - users_with_membership

    user_counts_by_tenant = {
        resolution.tenant_id: resolution.user_count
        for resolution in report.tenant_resolutions
    }
    users_unresolved_no_admin_tenant = sum(
        user_counts_by_tenant[tenant_id] for tenant_id in tenants_unresolved_no_admin
    )
    users_unresolved_no_business_tenant = sum(
        user_counts_by_tenant[tenant_id] for tenant_id in tenants_unresolved_no_business
    )
    users_unresolved_plain_role = (
        db.query(func.count(User.id))
        .filter(User.tenant_id.in_(globally_eligible_tenant_ids))
        .filter(~User.role.in_(ADMIN_ROLES))
        .scalar()
        if globally_eligible_tenant_ids
        else 0
    )

    tenants_pending_owner_confirmation = _tenant_ids_pending_owner_confirmation(
        db,
        tenant_ids=globally_eligible_tenant_ids,
        business_ids_by_tenant=business_ids_by_tenant,
    )

    return MembershipBackfillReport(
        generated_at=datetime.now(timezone.utc),
        tenants_total=len(report.tenant_resolutions),
        tenants_unresolved_no_admin=tenants_unresolved_no_admin,
        tenants_unresolved_no_business=tenants_unresolved_no_business,
        tenants_pending_owner_confirmation=tenants_pending_owner_confirmation,
        memberships_created=memberships_created,
        memberships_skipped_existing=memberships_skipped_existing,
        users_total=users_total,
        users_with_membership=users_with_membership,
        users_unresolved=users_unresolved,
        users_unresolved_no_admin_tenant=users_unresolved_no_admin_tenant,
        users_unresolved_no_business_tenant=users_unresolved_no_business_tenant,
        users_unresolved_plain_role=users_unresolved_plain_role,
    )


def render_backfill_report_text(report: MembershipBackfillReport) -> str:
    lines = [
        f"Membership backfill report (generated {report.generated_at.isoformat()})",
        "",
        f"tenants_total={report.tenants_total}",
        f"tenants_unresolved_no_admin={len(report.tenants_unresolved_no_admin)} "
        f"{list(report.tenants_unresolved_no_admin)}",
        f"tenants_unresolved_no_business={len(report.tenants_unresolved_no_business)} "
        f"{list(report.tenants_unresolved_no_business)}",
        f"tenants_pending_owner_confirmation="
        f"{len(report.tenants_pending_owner_confirmation)} "
        f"{list(report.tenants_pending_owner_confirmation)}",
        "",
        f"memberships_created={report.memberships_created}",
        f"memberships_skipped_existing={report.memberships_skipped_existing}",
        "",
        f"users_total={report.users_total}",
        f"users_with_membership={report.users_with_membership}",
        f"users_unresolved={report.users_unresolved}",
        f"  users_unresolved_no_admin_tenant={report.users_unresolved_no_admin_tenant}",
        f"  users_unresolved_no_business_tenant={report.users_unresolved_no_business_tenant}",
        f"  users_unresolved_plain_role={report.users_unresolved_plain_role}",
    ]
    return "\n".join(lines)


def main() -> None:
    configure_logging()
    db = SessionLocal()

    try:
        report = run_membership_backfill(db)
        print(render_backfill_report_text(report))
    finally:
        db.close()


if __name__ == "__main__":
    main()
