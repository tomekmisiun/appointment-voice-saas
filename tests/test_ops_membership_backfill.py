"""SAC-004 membership backfill tests.

Fixture states mirror the "Dry-run examples" in
docs/specs/sac-002-membership-migration-runbook.md so the tests double as a
direct check against that runbook's documented examples.
"""
import uuid

from app.models.audit_log import AuditAction, AuditLog
from app.models.business import Business
from app.models.business_membership import (
    BusinessMembership,
    MembershipRole,
    MembershipStatus,
)
from app.models.tenant import Tenant
from app.models.user import User
from app.ops.membership_backfill import (
    list_business_ids_by_tenant,
    render_backfill_report_text,
    run_membership_backfill,
    tenant_eligible_for_backfill,
)
from app.ops.membership_preflight import (
    REASON_DUPLICATE_EMAIL_ACROSS_TENANTS,
    REASON_NO_ADMIN,
    REASON_NO_BUSINESS,
    TenantResolution,
)


def _unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _unique_email(local_part: str) -> str:
    return f"{local_part}-{uuid.uuid4().hex[:12]}@example.com"


def _create_tenant(db, prefix: str) -> Tenant:
    tenant = Tenant(slug=_unique_slug(prefix), name=prefix, is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def _create_business(db, tenant: Tenant, name: str = "Business") -> Business:
    business = Business(tenant_id=tenant.id, name=name, timezone="UTC", is_active=True)
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


def _create_user(db, tenant: Tenant, email: str, role: str = "user") -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        hashed_password="hashed-password",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _memberships_for_business(db, business_id: int) -> list[BusinessMembership]:
    return (
        db.query(BusinessMembership)
        .filter(BusinessMembership.business_id == business_id)
        .order_by(BusinessMembership.user_id)
        .all()
    )


def test_tenant_eligible_for_backfill_requires_admin_and_business():
    eligible = TenantResolution(
        tenant_id=1, tenant_slug="x", business_count=1, user_count=1, admin_count=1,
        reasons=(REASON_DUPLICATE_EMAIL_ACROSS_TENANTS,),
    )
    no_admin = TenantResolution(
        tenant_id=2, tenant_slug="y", business_count=1, user_count=1, admin_count=0,
        reasons=(REASON_NO_ADMIN,),
    )
    no_business = TenantResolution(
        tenant_id=3, tenant_slug="z", business_count=0, user_count=1, admin_count=1,
        reasons=(REASON_NO_BUSINESS,),
    )

    assert tenant_eligible_for_backfill(eligible) is True
    assert tenant_eligible_for_backfill(no_admin) is False
    assert tenant_eligible_for_backfill(no_business) is False


def test_list_business_ids_by_tenant_groups_by_tenant(db):
    tenant = _create_tenant(db, "sac004-list-biz")
    business_a = _create_business(db, tenant, "A")
    business_b = _create_business(db, tenant, "B")

    grouped = list_business_ids_by_tenant(db, (tenant.id,))

    assert set(grouped[tenant.id]) == {business_a.id, business_b.id}


def test_list_business_ids_by_tenant_returns_empty_for_no_tenant_ids(db):
    assert list_business_ids_by_tenant(db, ()) == {}


def test_self_signup_tenant_gets_admin_not_owner_membership(db):
    """Runbook dry-run example 1."""
    tenant = _create_tenant(db, "sac004-self-signup")
    business = _create_business(db, tenant)
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")
    plain_user = _create_user(db, tenant, _unique_email("plain"), role="user")
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            admin_id=None,
            action=AuditAction.TENANT_CREATED,
            source="self_signup",
        )
    )
    db.commit()

    run_membership_backfill(db, tenant_ids=(tenant.id,))

    memberships = _memberships_for_business(db, business.id)
    assert len(memberships) == 1
    assert memberships[0].user_id == admin.id
    assert memberships[0].role == MembershipRole.ADMIN
    assert memberships[0].status == MembershipStatus.ACTIVE
    assert not any(m.user_id == plain_user.id for m in memberships)


def test_safe_counts_without_signup_evidence_gets_admin_membership(db):
    """Runbook dry-run example 2."""
    tenant = _create_tenant(db, "sac004-safe-no-signup")
    business = _create_business(db, tenant)
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")

    run_membership_backfill(db, tenant_ids=(tenant.id,))

    memberships = _memberships_for_business(db, business.id)
    assert len(memberships) == 1
    assert memberships[0].user_id == admin.id
    assert memberships[0].role == MembershipRole.ADMIN


def test_multiple_admins_each_get_admin_membership_no_owner(db):
    """Runbook dry-run example 3."""
    tenant = _create_tenant(db, "sac004-multi-admin")
    business = _create_business(db, tenant)
    admin_a = _create_user(db, tenant, _unique_email("admin-a"), role="admin")
    admin_b = _create_user(db, tenant, _unique_email("admin-b"), role="admin")

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))

    memberships = _memberships_for_business(db, business.id)
    assert {m.user_id for m in memberships} == {admin_a.id, admin_b.id}
    assert all(m.role == MembershipRole.ADMIN for m in memberships)
    assert tenant.id in report.tenants_pending_owner_confirmation


def test_tenant_without_admin_gets_no_membership(db):
    """Runbook dry-run example 4."""
    tenant = _create_tenant(db, "sac004-no-admin")
    business = _create_business(db, tenant)
    _create_user(db, tenant, _unique_email("plain"), role="user")

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))

    assert _memberships_for_business(db, business.id) == []
    assert tenant.id in report.tenants_unresolved_no_admin


def test_tenant_without_business_gets_no_membership(db):
    tenant = _create_tenant(db, "sac004-no-business")
    _create_user(db, tenant, _unique_email("admin"), role="admin")

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))

    assert tenant.id in report.tenants_unresolved_no_business
    assert (
        db.query(BusinessMembership)
        .filter(BusinessMembership.tenant_id == tenant.id)
        .count()
        == 0
    )


def test_cross_tenant_duplicate_email_does_not_merge_memberships(db):
    """Runbook dry-run example 5."""
    local_part = f"sac004-dup-{uuid.uuid4().hex[:12]}"
    shared_email_a = f"{local_part}@example.com"
    shared_email_b = f"{local_part.upper()}@EXAMPLE.com"

    tenant_a = _create_tenant(db, "sac004-dup-a")
    business_a = _create_business(db, tenant_a)
    admin_a = _create_user(db, tenant_a, shared_email_a, role="admin")

    tenant_b = _create_tenant(db, "sac004-dup-b")
    business_b = _create_business(db, tenant_b)
    admin_b = _create_user(db, tenant_b, shared_email_b, role="admin")

    run_membership_backfill(db, tenant_ids=(tenant_a.id, tenant_b.id))

    memberships_a = _memberships_for_business(db, business_a.id)
    memberships_b = _memberships_for_business(db, business_b.id)

    assert len(memberships_a) == 1
    assert memberships_a[0].user_id == admin_a.id
    assert memberships_a[0].tenant_id == tenant_a.id

    assert len(memberships_b) == 1
    assert memberships_b[0].user_id == admin_b.id
    assert memberships_b[0].tenant_id == tenant_b.id


def test_one_membership_created_per_business_for_multi_business_tenant(db):
    tenant = _create_tenant(db, "sac004-multi-biz")
    business_a = _create_business(db, tenant, "A")
    business_b = _create_business(db, tenant, "B")
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")

    run_membership_backfill(db, tenant_ids=(tenant.id,))

    assert {m.user_id for m in _memberships_for_business(db, business_a.id)} == {admin.id}
    assert {m.user_id for m in _memberships_for_business(db, business_b.id)} == {admin.id}


def test_rerun_against_same_database_creates_no_new_memberships(db):
    tenant = _create_tenant(db, "sac004-idempotent")
    business = _create_business(db, tenant)
    _create_user(db, tenant, _unique_email("admin"), role="admin")

    first_report = run_membership_backfill(db, tenant_ids=(tenant.id,))
    assert first_report.memberships_created >= 1

    rows_after_first_run = _memberships_for_business(db, business.id)

    second_report = run_membership_backfill(db, tenant_ids=(tenant.id,))

    assert second_report.memberships_created == 0
    assert second_report.memberships_skipped_existing >= first_report.memberships_created
    assert _memberships_for_business(db, business.id) == rows_after_first_run


def test_backfill_does_not_invalidate_any_user_session(db):
    tenant = _create_tenant(db, "sac004-no-session-bump")
    _create_business(db, tenant)
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")
    token_version_before = admin.token_version

    run_membership_backfill(db, tenant_ids=(tenant.id,))

    db.refresh(admin)
    assert admin.token_version == token_version_before


def test_report_satisfies_users_with_membership_plus_unresolved_invariant(db):
    tenant = _create_tenant(db, "sac004-invariant")
    _create_business(db, tenant)
    _create_user(db, tenant, _unique_email("admin"), role="admin")

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))

    assert report.users_with_membership + report.users_unresolved == report.users_total


def test_tenant_ids_scopes_writes_to_only_the_given_tenants(db):
    tenant_in_scope = _create_tenant(db, "sac004-scope-in")
    business_in_scope = _create_business(db, tenant_in_scope)
    admin_in_scope = _create_user(db, tenant_in_scope, _unique_email("admin"), role="admin")

    tenant_out_of_scope = _create_tenant(db, "sac004-scope-out")
    business_out_of_scope = _create_business(db, tenant_out_of_scope)
    _create_user(db, tenant_out_of_scope, _unique_email("admin"), role="admin")

    report = run_membership_backfill(db, tenant_ids=(tenant_in_scope.id,))

    assert {m.user_id for m in _memberships_for_business(db, business_in_scope.id)} == {
        admin_in_scope.id
    }
    # Out-of-scope tenant gets no membership rows written this call...
    assert _memberships_for_business(db, business_out_of_scope.id) == []
    # ...but the pending-owner-confirmation count is a global verification
    # count, not scoped to this call's writes -- see run_membership_backfill's
    # docstring -- so it still includes the out-of-scope tenant.
    assert tenant_in_scope.id in report.tenants_pending_owner_confirmation
    assert tenant_out_of_scope.id in report.tenants_pending_owner_confirmation


def test_plain_role_unresolved_count_stays_global_during_a_scoped_run(db):
    tenant_in_scope = _create_tenant(db, "sac004-plain-scope-in")
    _create_business(db, tenant_in_scope)
    _create_user(db, tenant_in_scope, _unique_email("admin"), role="admin")
    _create_user(db, tenant_in_scope, _unique_email("plain"), role="user")

    tenant_out_of_scope = _create_tenant(db, "sac004-plain-scope-out")
    _create_business(db, tenant_out_of_scope)
    _create_user(db, tenant_out_of_scope, _unique_email("admin"), role="admin")
    _create_user(db, tenant_out_of_scope, _unique_email("plain"), role="user")

    scoped_report = run_membership_backfill(db, tenant_ids=(tenant_in_scope.id,))
    global_report = run_membership_backfill(db)

    # The plain-role decomposition is a global verification count (like
    # tenants_pending_owner_confirmation), so scoping writes to one tenant
    # must not omit the other tenant's plain-role user from the count.
    assert (
        scoped_report.users_unresolved_plain_role
        == global_report.users_unresolved_plain_role
    )


def test_tenant_pending_owner_confirmation_clears_once_every_business_has_an_owner(db):
    tenant = _create_tenant(db, "sac004-owner-confirmed")
    business = _create_business(db, tenant)
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")

    first_report = run_membership_backfill(db, tenant_ids=(tenant.id,))
    assert tenant.id in first_report.tenants_pending_owner_confirmation

    membership = (
        db.query(BusinessMembership)
        .filter(BusinessMembership.business_id == business.id, BusinessMembership.user_id == admin.id)
        .one()
    )
    membership.role = MembershipRole.OWNER
    db.commit()

    second_report = run_membership_backfill(db, tenant_ids=(tenant.id,))
    assert tenant.id not in second_report.tenants_pending_owner_confirmation


def test_tenant_pending_owner_confirmation_stays_pending_if_any_business_lacks_an_owner(db):
    tenant = _create_tenant(db, "sac004-partial-owner")
    business_a = _create_business(db, tenant, "A")
    _create_business(db, tenant, "B")
    admin = _create_user(db, tenant, _unique_email("admin"), role="admin")

    run_membership_backfill(db, tenant_ids=(tenant.id,))

    membership_a = (
        db.query(BusinessMembership)
        .filter(BusinessMembership.business_id == business_a.id, BusinessMembership.user_id == admin.id)
        .one()
    )
    membership_a.role = MembershipRole.OWNER
    db.commit()
    # business_b's membership is intentionally left as admin, not owner.

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))
    assert tenant.id in report.tenants_pending_owner_confirmation


def test_render_backfill_report_text_includes_all_counts(db):
    tenant = _create_tenant(db, "sac004-render")
    _create_business(db, tenant)
    _create_user(db, tenant, _unique_email("admin"), role="admin")

    report = run_membership_backfill(db, tenant_ids=(tenant.id,))
    text = render_backfill_report_text(report)

    assert "memberships_created=" in text
    assert "users_unresolved_plain_role=" in text
    assert tenant.id in report.tenants_pending_owner_confirmation
    assert str(tenant.id) in text
