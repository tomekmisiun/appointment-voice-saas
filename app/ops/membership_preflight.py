"""SAC-001: read-only membership/staff data preflight.

Produces deterministic counts and ambiguity reports so the membership
schema (SAC-003) and backfill (SAC-004) can be designed from evidence
instead of assumptions. No schema or data mutation -- see
docs/product/staff-access-calendar-roadmap.md and
docs/adr/0007-separate-staff-records-from-login-identities.md.

Run in production with:
    docker compose run --rm api python -m app.ops.membership_preflight

Emails and phone numbers are masked in the rendered report; do not
redirect raw output into a file tracked by git.
"""
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.models.audit_log import AuditAction, AuditLog
from app.models.business import Business
from app.models.calendar_integration import CalendarIntegration
from app.models.staff import Staff
from app.models.tenant import Tenant
from app.models.user import User

ADMIN_ROLES = ("admin", "platform_admin")

REASON_NO_BUSINESS = "no_business"
REASON_MULTIPLE_BUSINESSES = "multiple_businesses"
REASON_NO_ADMIN = "no_admin"
REASON_MULTIPLE_ADMINS = "multiple_admins"
REASON_DUPLICATE_EMAIL_ACROSS_TENANTS = "duplicate_email_across_tenants"


def mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if not domain:
        return "***"
    visible = local[:1] or "*"
    return f"{visible}***@{domain}"


def mask_phone(phone: str) -> str:
    tail = phone[-2:] if len(phone) >= 2 else phone
    return f"***{tail}"


@dataclass(frozen=True)
class TenantBusinessCount:
    tenant_id: int
    tenant_slug: str
    business_count: int


@dataclass(frozen=True)
class DuplicateEmailGroup:
    masked_email: str
    tenant_ids: tuple[int, ...]


@dataclass(frozen=True)
class AdminUserRow:
    tenant_id: int
    user_id: int
    role: str
    masked_email: str


@dataclass(frozen=True)
class SignupOwnershipRow:
    tenant_id: int
    tenant_slug: str
    source: str | None
    admin_user_count: int


@dataclass(frozen=True)
class StaffContactRow:
    staff_id: int
    tenant_id: int
    business_id: int
    has_phone: bool
    masked_phone: str | None


@dataclass(frozen=True)
class OrphanStaffReference:
    staff_id: int
    staff_tenant_id: int
    business_id: int
    business_tenant_id: int


@dataclass(frozen=True)
class CalendarIntegrationSummary:
    provider: str
    level: str
    count: int


@dataclass(frozen=True)
class TenantResolution:
    tenant_id: int
    tenant_slug: str
    business_count: int
    user_count: int
    admin_count: int
    reasons: tuple[str, ...]

    @property
    def is_safe(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class MembershipPreflightReport:
    generated_at: datetime
    tenant_business_counts: tuple[TenantBusinessCount, ...]
    duplicate_cross_tenant_emails: tuple[DuplicateEmailGroup, ...]
    admin_users: tuple[AdminUserRow, ...]
    signup_ownership: tuple[SignupOwnershipRow, ...]
    staff_contact_candidates: tuple[StaffContactRow, ...]
    orphan_staff_references: tuple[OrphanStaffReference, ...]
    calendar_integrations: tuple[CalendarIntegrationSummary, ...]
    tenant_resolutions: tuple[TenantResolution, ...]

    @property
    def safe_tenant_ids(self) -> tuple[int, ...]:
        return tuple(r.tenant_id for r in self.tenant_resolutions if r.is_safe)

    @property
    def tenants_needing_manual_resolution(self) -> tuple[TenantResolution, ...]:
        return tuple(r for r in self.tenant_resolutions if not r.is_safe)


def count_businesses_per_tenant(db: Session) -> tuple[TenantBusinessCount, ...]:
    rows = (
        db.query(Tenant.id, Tenant.slug, func.count(Business.id))
        .outerjoin(Business, Business.tenant_id == Tenant.id)
        .group_by(Tenant.id, Tenant.slug)
        .order_by(Tenant.id)
        .all()
    )
    return tuple(
        TenantBusinessCount(tenant_id=tenant_id, tenant_slug=slug, business_count=count)
        for tenant_id, slug, count in rows
    )


def find_duplicate_cross_tenant_emails(db: Session) -> tuple[DuplicateEmailGroup, ...]:
    normalized_email = func.lower(User.email)
    duplicate_emails = (
        db.query(normalized_email)
        .group_by(normalized_email)
        .having(func.count(func.distinct(User.tenant_id)) > 1)
        .all()
    )

    groups = []
    for (email,) in duplicate_emails:
        tenant_ids = (
            db.query(User.tenant_id)
            .filter(func.lower(User.email) == email)
            .distinct()
            .order_by(User.tenant_id)
            .all()
        )
        groups.append(
            DuplicateEmailGroup(
                masked_email=mask_email(email),
                tenant_ids=tuple(tenant_id for (tenant_id,) in tenant_ids),
            )
        )

    return tuple(groups)


def count_users_per_tenant(db: Session) -> dict[int, int]:
    rows = db.query(User.tenant_id, func.count(User.id)).group_by(User.tenant_id).all()
    return {tenant_id: count for tenant_id, count in rows}


def list_admin_users(db: Session) -> tuple[AdminUserRow, ...]:
    rows = (
        db.query(User.tenant_id, User.id, User.role, User.email)
        .filter(User.role.in_(ADMIN_ROLES))
        .order_by(User.tenant_id, User.id)
        .all()
    )
    return tuple(
        AdminUserRow(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            masked_email=mask_email(email),
        )
        for tenant_id, user_id, role, email in rows
    )


def summarize_signup_ownership(db: Session) -> tuple[SignupOwnershipRow, ...]:
    admin_counts: dict[int, int] = {}
    for row in list_admin_users(db):
        admin_counts[row.tenant_id] = admin_counts.get(row.tenant_id, 0) + 1

    tenant_slugs = {
        tenant_id: slug for tenant_id, slug in db.query(Tenant.id, Tenant.slug).all()
    }

    tenant_created_logs = (
        db.query(AuditLog.tenant_id, AuditLog.source)
        .filter(AuditLog.action == AuditAction.TENANT_CREATED)
        .order_by(AuditLog.tenant_id)
        .all()
    )

    return tuple(
        SignupOwnershipRow(
            tenant_id=tenant_id,
            tenant_slug=tenant_slugs.get(tenant_id, "?"),
            source=source,
            admin_user_count=admin_counts.get(tenant_id, 0),
        )
        for tenant_id, source in tenant_created_logs
    )


def find_staff_contact_candidates(db: Session) -> tuple[StaffContactRow, ...]:
    rows = (
        db.query(Staff.id, Staff.tenant_id, Staff.business_id, Staff.phone)
        .order_by(Staff.tenant_id, Staff.id)
        .all()
    )
    return tuple(
        StaffContactRow(
            staff_id=staff_id,
            tenant_id=tenant_id,
            business_id=business_id,
            has_phone=phone is not None,
            masked_phone=mask_phone(phone) if phone else None,
        )
        for staff_id, tenant_id, business_id, phone in rows
    )


def find_orphan_staff_references(db: Session) -> tuple[OrphanStaffReference, ...]:
    rows = (
        db.query(Staff.id, Staff.tenant_id, Staff.business_id, Business.tenant_id)
        .join(Business, Business.id == Staff.business_id)
        .filter(Staff.tenant_id != Business.tenant_id)
        .order_by(Staff.id)
        .all()
    )
    return tuple(
        OrphanStaffReference(
            staff_id=staff_id,
            staff_tenant_id=staff_tenant_id,
            business_id=business_id,
            business_tenant_id=business_tenant_id,
        )
        for staff_id, staff_tenant_id, business_id, business_tenant_id in rows
    )


def summarize_calendar_integrations(db: Session) -> tuple[CalendarIntegrationSummary, ...]:
    is_staff_level = CalendarIntegration.staff_id.isnot(None)
    rows = (
        db.query(
            CalendarIntegration.provider,
            is_staff_level,
            func.count(CalendarIntegration.id),
        )
        .group_by(CalendarIntegration.provider, is_staff_level)
        .order_by(CalendarIntegration.provider)
        .all()
    )
    return tuple(
        CalendarIntegrationSummary(
            provider=provider,
            level="staff" if staff_level else "business",
            count=count,
        )
        for provider, staff_level, count in rows
    )


def _compute_tenant_resolutions(
    tenant_business_counts: tuple[TenantBusinessCount, ...],
    admin_users: tuple[AdminUserRow, ...],
    duplicate_cross_tenant_emails: tuple[DuplicateEmailGroup, ...],
    user_counts: dict[int, int],
) -> tuple[TenantResolution, ...]:
    admin_counts: dict[int, int] = {}
    for row in admin_users:
        admin_counts[row.tenant_id] = admin_counts.get(row.tenant_id, 0) + 1

    tenants_with_duplicate_emails: set[int] = set()
    for group in duplicate_cross_tenant_emails:
        tenants_with_duplicate_emails.update(group.tenant_ids)

    resolutions = []
    for tenant_business_count in tenant_business_counts:
        reasons = []

        if tenant_business_count.business_count == 0:
            reasons.append(REASON_NO_BUSINESS)
        elif tenant_business_count.business_count > 1:
            reasons.append(REASON_MULTIPLE_BUSINESSES)

        admin_count = admin_counts.get(tenant_business_count.tenant_id, 0)
        if admin_count == 0:
            reasons.append(REASON_NO_ADMIN)
        elif admin_count > 1:
            reasons.append(REASON_MULTIPLE_ADMINS)

        if tenant_business_count.tenant_id in tenants_with_duplicate_emails:
            reasons.append(REASON_DUPLICATE_EMAIL_ACROSS_TENANTS)

        resolutions.append(
            TenantResolution(
                tenant_id=tenant_business_count.tenant_id,
                tenant_slug=tenant_business_count.tenant_slug,
                business_count=tenant_business_count.business_count,
                user_count=user_counts.get(tenant_business_count.tenant_id, 0),
                admin_count=admin_count,
                reasons=tuple(reasons),
            )
        )

    return tuple(resolutions)


def build_membership_preflight_report(db: Session) -> MembershipPreflightReport:
    tenant_business_counts = count_businesses_per_tenant(db)
    duplicate_cross_tenant_emails = find_duplicate_cross_tenant_emails(db)
    admin_users = list_admin_users(db)
    user_counts = count_users_per_tenant(db)

    return MembershipPreflightReport(
        generated_at=datetime.now(timezone.utc),
        tenant_business_counts=tenant_business_counts,
        duplicate_cross_tenant_emails=duplicate_cross_tenant_emails,
        admin_users=admin_users,
        signup_ownership=summarize_signup_ownership(db),
        staff_contact_candidates=find_staff_contact_candidates(db),
        orphan_staff_references=find_orphan_staff_references(db),
        calendar_integrations=summarize_calendar_integrations(db),
        tenant_resolutions=_compute_tenant_resolutions(
            tenant_business_counts, admin_users, duplicate_cross_tenant_emails, user_counts
        ),
    )


def render_report_text(report: MembershipPreflightReport) -> str:
    lines = [
        f"Membership data preflight report (generated {report.generated_at.isoformat()})",
        "",
        f"Tenants: {len(report.tenant_business_counts)}",
        f"Safe tenants (single business, single admin, no cross-tenant email "
        f"duplicate): {len(report.safe_tenant_ids)}",
        f"Tenants needing manual resolution: {len(report.tenants_needing_manual_resolution)}",
        "",
        "-- Tenant summary (businesses / users / admins) --",
    ]
    for resolution in report.tenant_resolutions:
        status = "safe" if resolution.is_safe else "manual_resolution"
        line = (
            f"tenant_id={resolution.tenant_id} slug={resolution.tenant_slug} "
            f"businesses={resolution.business_count} users={resolution.user_count} "
            f"admins={resolution.admin_count} status={status}"
        )
        if resolution.reasons:
            line += f" reasons={','.join(resolution.reasons)}"
        lines.append(line)
    if not report.tenant_resolutions:
        lines.append("none")

    lines.append("")
    lines.append("-- Admin users --")
    for row in report.admin_users:
        lines.append(
            f"tenant_id={row.tenant_id} user_id={row.user_id} role={row.role} "
            f"email={row.masked_email}"
        )
    if not report.admin_users:
        lines.append("none")

    lines.append("")
    lines.append("-- Duplicate cross-tenant emails --")
    for group in report.duplicate_cross_tenant_emails:
        lines.append(f"{group.masked_email} tenant_ids={list(group.tenant_ids)}")
    if not report.duplicate_cross_tenant_emails:
        lines.append("none")

    lines.append("")
    lines.append("-- Signup ownership evidence --")
    for row in report.signup_ownership:
        lines.append(
            f"tenant_id={row.tenant_id} slug={row.tenant_slug} source={row.source} "
            f"admin_user_count={row.admin_user_count}"
        )
    if not report.signup_ownership:
        lines.append("none")

    lines.append("")
    lines.append("-- Staff contact candidates --")
    with_phone = sum(1 for row in report.staff_contact_candidates if row.has_phone)
    lines.append(
        f"{with_phone}/{len(report.staff_contact_candidates)} staff rows have a phone number"
    )

    lines.append("")
    lines.append("-- Orphan/mismatched staff references --")
    for row in report.orphan_staff_references:
        lines.append(
            f"staff_id={row.staff_id} staff_tenant_id={row.staff_tenant_id} "
            f"business_id={row.business_id} business_tenant_id={row.business_tenant_id}"
        )
    if not report.orphan_staff_references:
        lines.append("none")

    lines.append("")
    lines.append("-- Existing calendar integrations --")
    for summary in report.calendar_integrations:
        lines.append(f"provider={summary.provider} level={summary.level} count={summary.count}")
    if not report.calendar_integrations:
        lines.append("none")

    return "\n".join(lines)


def main() -> None:
    configure_logging()
    db = SessionLocal()

    try:
        report = build_membership_preflight_report(db)
        print(render_report_text(report))
    finally:
        db.close()


if __name__ == "__main__":
    main()
