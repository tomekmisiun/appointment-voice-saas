"""P3-012: manual admin override workflow (force booking/cancel with a
mandatory reason and a distinct, queryable audit trail).

Decision recorded for this task: override-create does NOT bypass the
DB-level no-overlap exclusion constraint (`no_overlapping_staff_bookings`)
for a staff_id with a real conflict. It only adds a mandatory reason and a
distinct AuditAction for cases that are not otherwise blocked (no staff_id,
or no actual conflict) — see docs/audits/pre-p3-readiness-audit.md §10 and
the override-create-still-409s test below, which documents this boundary
on purpose rather than leaving it implicit.
"""
from datetime import datetime, timezone

from app.core.domain_errors import BadRequestError
from app.models.audit_log import AuditAction
from app.models.booking import BookingStatus
from app.models.business_membership import BusinessMembership, MembershipRole, MembershipStatus
from app.models.tenant import Tenant
from app.models.user import User
from app.services.audit_log_service import get_audit_logs
from app.services.booking_service import cancel_booking, create_booking
from app.services.business_service import create_business
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _give_admin_membership(db, email: str, biz) -> None:
    user = db.query(User).filter(User.email == email).one()
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id,
        business_id=biz.id,
        user_id=user.id,
        role=MembershipRole.ADMIN,
        status=MembershipStatus.ACTIVE,
    ))
    db.commit()


def _dt(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Override Salon", timezone="UTC")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Anna")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48670000001")
    return tenant.id, biz, staff, svc, customer


# --- service layer: reason required, distinct audit action ---


def test_override_create_requires_reason(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    try:
        create_booking(
            db,
            tenant_id=tenant_id,
            business_id=biz.id,
            customer_id=customer.id,
            service_id=svc.id,
            staff_id=None,
            starts_at=_dt(2027, 3, 1, 9),
            override=True,
            reason="   ",
        )
        raise AssertionError("expected BadRequestError")
    except BadRequestError:
        pass


def test_override_create_logs_distinct_audit_action(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 3, 2, 9),
        override=True,
        reason="VIP walk-in, manager approved",
    )

    logs = get_audit_logs(db, tenant_id)
    entry = next((log for log in logs if log.target_booking_id == booking.id), None)
    assert entry is not None
    assert entry.action == AuditAction.BOOKING_OVERRIDE_CREATED
    assert entry.source == "VIP walk-in, manager approved"


def test_override_create_still_blocked_by_real_staff_conflict(db):
    """Documents the Option 1 boundary: override does not bypass the
    DB-level no_overlapping_staff_bookings constraint for a genuine
    same-staff conflict. Force-overbooking a specific staff slot is out of
    scope for this task (see module docstring)."""
    from app.core.domain_errors import ConflictError

    tenant_id, biz, staff, svc, customer = _setup(db)
    create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_dt(2027, 3, 3, 9),
    )

    try:
        create_booking(
            db,
            tenant_id=tenant_id,
            business_id=biz.id,
            customer_id=customer.id,
            service_id=svc.id,
            staff_id=staff.id,
            starts_at=_dt(2027, 3, 3, 9),
            override=True,
            reason="VIP wants this exact slot anyway",
        )
        raise AssertionError("expected ConflictError")
    except ConflictError:
        pass


def test_override_cancel_requires_reason(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 3, 4, 9),
    )

    try:
        cancel_booking(db, booking.id, biz.id, tenant_id, override=True, reason=None)
        raise AssertionError("expected BadRequestError")
    except BadRequestError:
        pass


def test_override_cancel_frees_slot_and_logs_distinct_audit_action(db):
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_dt(2027, 3, 5, 9),
    )

    cancel_booking(
        db, booking.id, biz.id, tenant_id, override=True, reason="staff emergency"
    )

    db.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancel_reason == "staff emergency"

    logs = get_audit_logs(db, tenant_id)
    entry = next((log for log in logs if log.target_booking_id == booking.id), None)
    assert entry is not None
    assert entry.action == AuditAction.BOOKING_OVERRIDE_CANCELLED
    assert entry.source == "staff emergency"

    # slot is genuinely free again -- a new booking for the same staff/time
    # succeeds without a conflict error.
    rebooked = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=_dt(2027, 3, 5, 9),
    )
    assert rebooked.status == BookingStatus.CONFIRMED


def test_regular_cancel_and_create_unaffected(db):
    """Regression: existing non-override paths keep logging the original
    AuditAction and source, unchanged by the override parameters."""
    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 3, 6, 9),
    )
    cancel_booking(db, booking.id, biz.id, tenant_id, reason="customer request")

    logs = get_audit_logs(db, tenant_id)
    create_entry = next(
        (log for log in logs if log.target_booking_id == booking.id and log.action == AuditAction.BOOKING_CREATED),
        None,
    )
    cancel_entry = next(
        (log for log in logs if log.target_booking_id == booking.id and log.action == AuditAction.BOOKING_CANCELLED),
        None,
    )
    assert create_entry is not None
    assert cancel_entry is not None


# --- API layer: admin-only, reason required, end-to-end ---


def test_override_create_api_endpoint(db, client):
    register_user(client, "override_admin@example.com")
    promote_to_admin(db, "override_admin@example.com")
    token = login_user(client, "override_admin@example.com").json()["access_token"]

    biz = client.post(
        "/api/v1/businesses",
        json={"name": "API Override Salon", "timezone": "UTC"},
        headers=auth_headers(token),
    ).json()
    svc = client.post(
        f"/api/v1/businesses/{biz['id']}/services",
        json={"name": "Trim", "duration_minutes": 15},
        headers=auth_headers(token),
    ).json()
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz["id"], phone="+48670000099"
    )

    resp = client.post(
        f"/api/v1/businesses/{biz['id']}/bookings/override",
        json={
            "customer_id": customer.id,
            "service_id": svc["id"],
            "starts_at": "2027-04-01T09:00:00+00:00",
            "reason": "manual walk-in",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "confirmed"


def test_override_create_api_requires_admin(db, client):
    register_user(client, "override_member@example.com")
    token = login_user(client, "override_member@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/override",
        json={
            "customer_id": customer.id,
            "service_id": svc.id,
            "starts_at": "2027-04-02T09:00:00+00:00",
            "reason": "manual walk-in",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_override_create_api_rejects_missing_reason(db, client):
    register_user(client, "override_noreason@example.com")
    promote_to_admin(db, "override_noreason@example.com")
    token = login_user(client, "override_noreason@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    _give_admin_membership(db, "override_noreason@example.com", biz)
    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/override",
        json={
            "customer_id": customer.id,
            "service_id": svc.id,
            "starts_at": "2027-04-03T09:00:00+00:00",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422


def test_override_cancel_api_endpoint(db, client):
    register_user(client, "override_cancel_admin@example.com")
    promote_to_admin(db, "override_cancel_admin@example.com")
    token = login_user(client, "override_cancel_admin@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    _give_admin_membership(db, "override_cancel_admin@example.com", biz)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 4, 4, 9),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/override-cancel",
        json={"reason": "support escalation"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_override_cancel_api_requires_admin(db, client):
    register_user(client, "override_cancel_member@example.com")
    token = login_user(client, "override_cancel_member@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 4, 5, 9),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/override-cancel",
        json={"reason": "support escalation"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


def test_override_cancel_api_rejects_blank_reason(db, client):
    register_user(client, "override_cancel_blank@example.com")
    promote_to_admin(db, "override_cancel_blank@example.com")
    token = login_user(client, "override_cancel_blank@example.com").json()["access_token"]

    tenant_id, biz, staff, svc, customer = _setup(db)
    _give_admin_membership(db, "override_cancel_blank@example.com", biz)
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=_dt(2027, 4, 6, 9),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/override-cancel",
        json={"reason": "   "},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
