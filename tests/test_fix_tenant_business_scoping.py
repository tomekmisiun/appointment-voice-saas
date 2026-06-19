"""Regression tests for the cross-business (same-tenant) data isolation fix.

Before this fix, several routes accepted a `business_id` path parameter but
the underlying service-layer lookups (`require_client`, `require_customer`,
`require_staff`, `require_booking`) only filtered by `tenant_id`. A user
authorized for one business could read or mutate another business's
Client/Customer/Staff/Booking rows -- including running GDPR anonymization
on another business's customer -- by substituting `business_id` in the URL
while keeping a valid resource id from a different business in the same
tenant. See docs/audits/pre-p3-readiness-audit.md Finding 1 (AVS-TD-029).
"""
from datetime import datetime, timedelta, timezone

from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.client_service import create_client
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from app.services.staff_service import create_staff
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _admin(db, client, email: str) -> str:
    register_user(client, email)
    promote_to_admin(db, email)
    return login_user(client, email).json()["access_token"]


def _two_businesses(db, tenant_id: int):
    biz_a = create_business(db, tenant_id=tenant_id, name="Business A", timezone="UTC")
    biz_b = create_business(db, tenant_id=tenant_id, name="Business B", timezone="UTC")
    return biz_a, biz_b


def test_get_client_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-client-get@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    client_a = create_client(db, tenant_id=tenant.id, business_id=biz_a.id, name="Client A")

    resp = client.get(
        f"/api/v1/businesses/{biz_b.id}/clients/{client_a.id}",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_update_client_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-client-patch@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    client_a = create_client(db, tenant_id=tenant.id, business_id=biz_a.id, name="Client A")

    resp = client.patch(
        f"/api/v1/businesses/{biz_b.id}/clients/{client_a.id}",
        json={"notes": "hijacked"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_client_bookings_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-client-bookings@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    client_a = create_client(db, tenant_id=tenant.id, business_id=biz_a.id, name="Client A")

    resp = client.get(
        f"/api/v1/businesses/{biz_b.id}/clients/{client_a.id}/bookings",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_gdpr_delete_rejects_cross_business_customer(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-gdpr@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    customer_a = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_a.id, phone="+48770000001", name="Real Name"
    )

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/customers/{customer_a.id}/gdpr-delete",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404
    db.refresh(customer_a)
    assert customer_a.name == "Real Name"


def test_get_staff_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-staff-get@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    staff_a = create_staff(db, tenant_id=tenant.id, business_id=biz_a.id, name="Stylist A")

    resp = client.get(
        f"/api/v1/businesses/{biz_b.id}/staff/{staff_a.id}",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_update_staff_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-staff-patch@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    staff_a = create_staff(db, tenant_id=tenant.id, business_id=biz_a.id, name="Stylist A")

    resp = client.patch(
        f"/api/v1/businesses/{biz_b.id}/staff/{staff_a.id}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404
    db.refresh(staff_a)
    assert staff_a.is_active is True


def _booking_in_business(db, tenant_id: int, biz, *, phone: str):
    svc = create_service(db, tenant_id=tenant_id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone=phone)
    from app.services.booking_service import create_booking

    return create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(days=5),
    )


def test_get_booking_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-get@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    booking_a = _booking_in_business(db, tenant.id, biz_a, phone="+48770000002")

    resp = client.get(
        f"/api/v1/businesses/{biz_b.id}/bookings/{booking_a.id}",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_cancel_booking_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-cancel@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    booking_a = _booking_in_business(db, tenant.id, biz_a, phone="+48770000003")

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/bookings/{booking_a.id}/cancel",
        json={"reason": "hijacked"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404
    db.refresh(booking_a)
    assert booking_a.status == "confirmed"


def test_reschedule_booking_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-reschedule@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    booking_a = _booking_in_business(db, tenant.id, biz_a, phone="+48770000004")

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/bookings/{booking_a.id}/reschedule",
        json={"new_starts_at": "2027-03-01T10:00:00+00:00"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404
    db.refresh(booking_a)
    assert booking_a.status == "confirmed"


def test_create_booking_rejects_customer_from_another_business(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-create@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    svc_b = create_service(db, tenant_id=tenant.id, business_id=biz_b.id, name="Cut", duration_minutes=30)
    customer_a = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_a.id, phone="+48770000005"
    )

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/bookings",
        json={
            "customer_id": customer_a.id,
            "service_id": svc_b.id,
            "starts_at": "2027-03-02T10:00:00+00:00",
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_create_booking_rejects_staff_from_another_business(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-create-staff@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    svc_b = create_service(db, tenant_id=tenant.id, business_id=biz_b.id, name="Cut", duration_minutes=30)
    customer_b = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_b.id, phone="+48770000006"
    )
    staff_a = create_staff(db, tenant_id=tenant.id, business_id=biz_a.id, name="Stylist A")

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/bookings",
        json={
            "customer_id": customer_b.id,
            "service_id": svc_b.id,
            "staff_id": staff_a.id,
            "starts_at": "2027-03-03T10:00:00+00:00",
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_create_client_rejects_customer_from_another_business(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-create-client@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    customer_a = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_a.id, phone="+48770000007"
    )

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/clients",
        json={"name": "Jane", "customer_id": customer_a.id},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_create_booking_rejects_service_from_another_business(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-booking-create-service@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    svc_a = create_service(db, tenant_id=tenant.id, business_id=biz_a.id, name="Cut", duration_minutes=30)
    customer_b = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_b.id, phone="+48770000008"
    )

    resp = client.post(
        f"/api/v1/businesses/{biz_b.id}/bookings",
        json={
            "customer_id": customer_b.id,
            "service_id": svc_a.id,
            "starts_at": "2027-03-04T10:00:00+00:00",
        },
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_get_service_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-service-get@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    svc_a = create_service(db, tenant_id=tenant.id, business_id=biz_a.id, name="Cut", duration_minutes=30)

    resp = client.get(
        f"/api/v1/businesses/{biz_b.id}/services/{svc_a.id}",
        headers=auth_headers(token),
    )

    assert resp.status_code == 404


def test_update_service_rejects_cross_business_access(db, client):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    token = _admin(db, client, "scope-service-patch@example.com")
    biz_a, biz_b = _two_businesses(db, tenant.id)
    svc_a = create_service(db, tenant_id=tenant.id, business_id=biz_a.id, name="Cut", duration_minutes=30)

    resp = client.patch(
        f"/api/v1/businesses/{biz_b.id}/services/{svc_a.id}",
        json={"name": "hijacked"},
        headers=auth_headers(token),
    )

    assert resp.status_code == 404
    db.refresh(svc_a)
    assert svc_a.name == "Cut"
