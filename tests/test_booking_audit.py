"""Tests for booking audit log (AVS-D006)."""

from datetime import datetime, timezone

from app.models.audit_log import AuditAction
from app.models.booking import BookingSource
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


_STARTS_AT = datetime(2027, 9, 1, 9, 0, 0, tzinfo=timezone.utc)


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Audit Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Piotr")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600900800")
    return tenant.id, biz.id, staff.id, svc.id, customer.id


def test_create_booking_emits_audit_log(db):
    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
        actor_id=None,
    )

    logs = get_audit_logs(db, tenant_id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CREATED and log.target_booking_id == booking.id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id is None
    assert entry.tenant_id == tenant_id
    assert entry.source == BookingSource.API


def test_create_booking_records_actor(db, client):
    register_user(client, "create-audit@example.com")
    promote_to_admin(db, "create-audit@example.com")
    actor = db.query(User).filter(User.email == "create-audit@example.com").one()

    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
        actor_id=actor.id,
        source=BookingSource.IVR,
    )

    logs = get_audit_logs(db, tenant_id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CREATED and log.target_booking_id == booking.id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id
    assert entry.source == BookingSource.IVR


def test_cancel_booking_emits_audit_log(db, client):
    register_user(client, "cancel-audit@example.com")
    promote_to_admin(db, "cancel-audit@example.com")
    actor = db.query(User).filter(User.email == "cancel-audit@example.com").one()

    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )
    cancel_booking(db, booking.id, biz_id, tenant_id, reason="No show", actor_id=actor.id)

    logs = get_audit_logs(db, tenant_id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CANCELLED and log.target_booking_id == booking.id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id
    assert entry.tenant_id == tenant_id
    assert entry.source == BookingSource.API


def test_reschedule_booking_emits_audit_log_linked_to_old_booking(db, client):
    register_user(client, "reschedule-audit@example.com")
    promote_to_admin(db, "reschedule-audit@example.com")
    actor = db.query(User).filter(User.email == "reschedule-audit@example.com").one()

    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)
    from app.services.booking_service import reschedule_booking

    old_booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
    )

    new_booking = reschedule_booking(
        db,
        old_booking.id,
        biz_id,
        tenant_id,
        new_starts_at=datetime(2027, 9, 2, 10, 0, 0, tzinfo=timezone.utc),
        actor_id=actor.id,
    )

    logs = get_audit_logs(db, tenant_id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_RESCHEDULED and log.target_booking_id == new_booking.id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id
    assert entry.source == f"rescheduled_from_booking_{old_booking.id}"

    cancelled_entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CANCELLED and log.target_booking_id == old_booking.id
        ),
        None,
    )
    assert cancelled_entry is not None


def test_audit_log_isolated_to_tenant(db):
    tenant_id, biz_id, staff_id, svc_id, customer_id = _setup(db)

    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz_id,
        customer_id=customer_id,
        service_id=svc_id,
        staff_id=staff_id,
        starts_at=_STARTS_AT,
        actor_id=None,
    )

    other_logs = get_audit_logs(db, tenant_id=99999)
    booking_logs = [log for log in other_logs if log.target_booking_id == booking.id]
    assert booking_logs == []


def test_api_create_booking_records_actor(db, client):
    register_user(client, "auditor@example.com")
    promote_to_admin(db, "auditor@example.com")
    actor = db.query(User).filter(User.email == "auditor@example.com").one()
    token = login_user(client, "auditor@example.com").json()["access_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="API Audit Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Kasia")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Trim", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600700600")
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id, business_id=biz.id, user_id=actor.id,
        role=MembershipRole.ADMIN, status=MembershipStatus.ACTIVE,
    ))
    db.commit()

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings",
        json={
            "customer_id": customer.id,
            "service_id": svc.id,
            "staff_id": staff.id,
            "starts_at": "2027-09-02T09:00:00Z",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 201
    booking_id = resp.json()["id"]

    logs = get_audit_logs(db, tenant.id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CREATED and log.target_booking_id == booking_id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id
    assert entry.source == BookingSource.API


def test_api_cancel_booking_records_actor(db, client):
    register_user(client, "auditor2@example.com")
    promote_to_admin(db, "auditor2@example.com")
    actor = db.query(User).filter(User.email == "auditor2@example.com").one()
    token = login_user(client, "auditor2@example.com").json()["access_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Cancel Audit Salon", timezone="Europe/Warsaw")
    staff = create_staff(db, tenant_id=tenant.id, business_id=biz.id, name="Tomek")
    svc = create_service(db, tenant_id=tenant.id, business_id=biz.id, name="Shave", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz.id, phone="+48600500400")
    db.add(BusinessMembership(
        tenant_id=biz.tenant_id, business_id=biz.id, user_id=actor.id,
        role=MembershipRole.ADMIN, status=MembershipStatus.ACTIVE,
    ))
    db.commit()

    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=staff.id,
        starts_at=datetime(2027, 9, 3, 9, 0, 0, tzinfo=timezone.utc),
    )

    resp = client.post(
        f"/api/v1/businesses/{biz.id}/bookings/{booking.id}/cancel",
        json={"reason": "Client request"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200

    logs = get_audit_logs(db, tenant.id)
    entry = next(
        (
            log for log in logs
            if log.action == AuditAction.BOOKING_CANCELLED and log.target_booking_id == booking.id
        ),
        None,
    )
    assert entry is not None
    assert entry.admin_id == actor.id
    assert entry.source == BookingSource.API
