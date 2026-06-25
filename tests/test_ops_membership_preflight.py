"""SAC-001 preflight report tests (read-only, no schema/data mutation)."""
import uuid

from app.models.audit_log import AuditAction, AuditLog
from app.models.business import Business
from app.models.calendar_integration import CalendarIntegration
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.models.user import User
from app.ops.membership_preflight import (
    build_membership_preflight_report,
    count_businesses_per_tenant,
    count_users_per_tenant,
    find_duplicate_cross_tenant_emails,
    find_orphan_staff_references,
    find_staff_contact_candidates,
    list_admin_users,
    mask_email,
    mask_phone,
    summarize_calendar_integrations,
    summarize_signup_ownership,
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


def test_mask_email_keeps_first_char_and_domain():
    assert mask_email("jane.doe@example.com") == "j***@example.com"


def test_mask_email_handles_value_without_domain():
    assert mask_email("not-an-email") == "***"


def test_mask_phone_keeps_last_two_digits():
    assert mask_phone("+15551234589") == "***89"


def test_count_businesses_per_tenant_distinguishes_single_and_multi_business_tenant(db):
    single_business_tenant = _create_tenant(db, "sac001-single")
    _create_business(db, single_business_tenant)

    multi_business_tenant = _create_tenant(db, "sac001-multi")
    _create_business(db, multi_business_tenant, "Branch A")
    _create_business(db, multi_business_tenant, "Branch B")

    counts_by_tenant_id = {
        row.tenant_id: row.business_count for row in count_businesses_per_tenant(db)
    }

    assert counts_by_tenant_id[single_business_tenant.id] == 1
    assert counts_by_tenant_id[multi_business_tenant.id] == 2


def test_count_users_per_tenant_counts_all_roles(db):
    tenant = _create_tenant(db, "sac001-user-counts")
    _create_user(db, tenant, _unique_email("owner"), role="admin")
    _create_user(db, tenant, _unique_email("staffer"), role="user")

    counts_by_tenant_id = count_users_per_tenant(db)

    assert counts_by_tenant_id[tenant.id] == 2


def test_find_duplicate_cross_tenant_emails_groups_case_insensitively(db):
    unique_local_part = f"sac001-dup-{uuid.uuid4().hex[:12]}"
    email_lower = f"{unique_local_part}@example.com"
    email_mixed_case = f"{unique_local_part.upper()}@EXAMPLE.com"

    tenant_a = _create_tenant(db, "sac001-dup-a")
    tenant_b = _create_tenant(db, "sac001-dup-b")
    _create_user(db, tenant_a, email_lower)
    _create_user(db, tenant_b, email_mixed_case)

    groups = find_duplicate_cross_tenant_emails(db)
    matching_groups = [
        g for g in groups if set(g.tenant_ids) == {tenant_a.id, tenant_b.id}
    ]

    assert len(matching_groups) == 1
    assert matching_groups[0].masked_email == mask_email(email_lower)


def test_find_duplicate_cross_tenant_emails_ignores_same_tenant_repeats(db):
    tenant = _create_tenant(db, "sac001-single-tenant")
    email = f"sac001-onlyone-{uuid.uuid4().hex[:12]}@example.com"
    _create_user(db, tenant, email)

    groups = find_duplicate_cross_tenant_emails(db)

    assert not any(tenant.id in g.tenant_ids for g in groups)


def test_list_admin_users_filters_by_role_and_masks_email(db):
    tenant = _create_tenant(db, "sac001-admins")
    owner_email = _unique_email("owner")
    admin = _create_user(db, tenant, owner_email, role="admin")
    _create_user(db, tenant, _unique_email("staffer"), role="user")

    rows = [row for row in list_admin_users(db) if row.tenant_id == tenant.id]

    assert len(rows) == 1
    assert rows[0].user_id == admin.id
    assert rows[0].role == "admin"
    assert rows[0].masked_email == mask_email(owner_email)


def test_summarize_signup_ownership_reports_source_and_admin_count(db):
    tenant = _create_tenant(db, "sac001-signup")
    _create_user(db, tenant, _unique_email("owner"), role="admin")
    db.add(
        AuditLog(
            tenant_id=tenant.id,
            admin_id=None,
            action=AuditAction.TENANT_CREATED,
            source="self_signup",
        )
    )
    db.commit()

    rows = [row for row in summarize_signup_ownership(db) if row.tenant_id == tenant.id]

    assert len(rows) == 1
    assert rows[0].source == "self_signup"
    assert rows[0].admin_user_count == 1


def test_find_staff_contact_candidates_flags_missing_phone(db):
    tenant = _create_tenant(db, "sac001-contact")
    business = _create_business(db, tenant)
    with_phone = Staff(
        tenant_id=tenant.id, business_id=business.id, name="Has Phone", phone="+15551234589",
        is_active=True,
    )
    without_phone = Staff(
        tenant_id=tenant.id, business_id=business.id, name="No Phone", is_active=True,
    )
    db.add_all([with_phone, without_phone])
    db.commit()
    db.refresh(with_phone)
    db.refresh(without_phone)

    rows_by_id = {row.staff_id: row for row in find_staff_contact_candidates(db)}

    assert rows_by_id[with_phone.id].has_phone is True
    assert rows_by_id[with_phone.id].masked_phone == "***89"
    assert rows_by_id[without_phone.id].has_phone is False
    assert rows_by_id[without_phone.id].masked_phone is None


def test_find_orphan_staff_references_detects_tenant_business_mismatch(db):
    tenant_a = _create_tenant(db, "sac001-orphan-a")
    tenant_b = _create_tenant(db, "sac001-orphan-b")
    business_a = _create_business(db, tenant_a)

    # Simulates pre-existing inconsistent data: a staff row whose tenant_id
    # does not match the tenant of its referenced business. The app-level
    # create_staff() service prevents this going forward (see
    # require_business() in staff_service.py); the audit must still surface
    # rows already in this state.
    mismatched_staff = Staff(
        tenant_id=tenant_b.id, business_id=business_a.id, name="Mismatched", is_active=True,
    )
    db.add(mismatched_staff)
    db.commit()
    db.refresh(mismatched_staff)

    rows_by_staff_id = {row.staff_id: row for row in find_orphan_staff_references(db)}

    assert mismatched_staff.id in rows_by_staff_id
    mismatch = rows_by_staff_id[mismatched_staff.id]
    assert mismatch.staff_tenant_id == tenant_b.id
    assert mismatch.business_tenant_id == tenant_a.id


def test_find_orphan_staff_references_excludes_consistent_staff(db):
    tenant = _create_tenant(db, "sac001-consistent")
    business = _create_business(db, tenant)
    consistent_staff = Staff(
        tenant_id=tenant.id, business_id=business.id, name="Consistent", is_active=True,
    )
    db.add(consistent_staff)
    db.commit()
    db.refresh(consistent_staff)

    rows_by_staff_id = {row.staff_id: row for row in find_orphan_staff_references(db)}

    assert consistent_staff.id not in rows_by_staff_id


def test_summarize_calendar_integrations_groups_by_provider_and_level(db):
    tenant = _create_tenant(db, "sac001-cal")
    business = _create_business(db, tenant)
    staff = Staff(tenant_id=tenant.id, business_id=business.id, name="Staffer", is_active=True)
    db.add(staff)
    db.commit()
    db.refresh(staff)

    unique_provider = f"sac001-test-provider-{uuid.uuid4().hex[:12]}"
    db.add_all(
        [
            CalendarIntegration(
                tenant_id=tenant.id, business_id=business.id, staff_id=None,
                provider=unique_provider, is_active=True,
            ),
            CalendarIntegration(
                tenant_id=tenant.id, business_id=business.id, staff_id=staff.id,
                provider=unique_provider, is_active=True,
            ),
        ]
    )
    db.commit()

    summaries = {
        (s.provider, s.level): s.count
        for s in summarize_calendar_integrations(db)
        if s.provider == unique_provider
    }

    assert summaries[(unique_provider, "business")] == 1
    assert summaries[(unique_provider, "staff")] == 1


def test_build_membership_preflight_report_marks_single_business_single_admin_tenant_safe(db):
    tenant = _create_tenant(db, "sac001-safe")
    _create_business(db, tenant)
    _create_user(db, tenant, _unique_email("owner"), role="admin")
    _create_user(db, tenant, _unique_email("staffer"), role="user")

    report = build_membership_preflight_report(db)

    assert tenant.id in report.safe_tenant_ids
    assert tenant.id not in {r.tenant_id for r in report.tenants_needing_manual_resolution}

    resolution = next(r for r in report.tenant_resolutions if r.tenant_id == tenant.id)
    assert resolution.business_count == 1
    assert resolution.user_count == 2
    assert resolution.admin_count == 1


def test_build_membership_preflight_report_flags_multiple_businesses_for_manual_resolution(db):
    tenant = _create_tenant(db, "sac001-unsafe")
    _create_business(db, tenant, "Branch A")
    _create_business(db, tenant, "Branch B")
    _create_user(db, tenant, _unique_email("owner"), role="admin")

    report = build_membership_preflight_report(db)

    resolutions_by_tenant_id = {r.tenant_id: r for r in report.tenants_needing_manual_resolution}

    assert tenant.id in resolutions_by_tenant_id
    assert "multiple_businesses" in resolutions_by_tenant_id[tenant.id].reasons
    assert resolutions_by_tenant_id[tenant.id].business_count == 2
    assert resolutions_by_tenant_id[tenant.id].user_count == 1
    assert tenant.id not in report.safe_tenant_ids


def test_build_membership_preflight_report_has_no_staff_or_integrations_for_empty_tenant(db):
    empty_tenant = _create_tenant(db, "sac001-empty")
    _create_business(db, empty_tenant)
    _create_user(db, empty_tenant, _unique_email("owner"), role="admin")

    report = build_membership_preflight_report(db)

    assert not [
        row for row in report.staff_contact_candidates if row.tenant_id == empty_tenant.id
    ]
    assert not [
        row for row in report.orphan_staff_references
        if row.staff_tenant_id == empty_tenant.id
    ]
