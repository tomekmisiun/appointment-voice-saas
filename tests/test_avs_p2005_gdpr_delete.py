"""P2-005: GDPR delete (anonymization) endpoint.

gdpr_delete_customer() anonymizes PII on a Customer (and any linked
Client) rather than hard-deleting the row: Booking.customer_id has no
ON DELETE clause, so a customer with booking history can't be removed
without breaking that FK, and removing the row would also break the
booking/audit trail the business is required to keep. Applies regardless
of booking status.
"""
from datetime import datetime, timedelta, timezone

from app.models.audit_log import AuditAction
from app.models.tenant import Tenant
from app.services.audit_log_service import get_audit_logs
from app.services.booking_service import create_booking
from app.services.business_service import create_business
from app.services.client_service import create_client
from app.services.customer_service import gdpr_delete_customer, get_or_create_customer
from app.services.service_service import create_service
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="GDPR Salon", timezone="UTC")
    return tenant.id, biz


def test_gdpr_delete_scrubs_customer_pii(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(
        db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000001", name="Real Name"
    )

    anonymized = gdpr_delete_customer(db, customer.id, tenant_id)

    assert anonymized.name is None
    assert anonymized.phone == "deleted"
    assert anonymized.phone_normalized == f"deleted-{customer.id}"


def test_gdpr_delete_scrubs_linked_client(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000002")
    client_row = create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Real Name",
        customer_id=customer.id, email="real@example.com", phone="+48740000002", notes="VIP",
    )

    gdpr_delete_customer(db, customer.id, tenant_id)

    db.refresh(client_row)
    assert client_row.name == "Deleted client"
    assert client_row.email is None
    assert client_row.phone is None
    assert client_row.notes is None


def test_gdpr_delete_preserves_booking_and_does_not_break_fk(db):
    tenant_id, biz = _setup(db)
    svc = create_service(db, tenant_id=tenant_id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000003")
    booking = create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(days=3),
    )

    gdpr_delete_customer(db, customer.id, tenant_id)

    db.refresh(booking)
    assert booking.customer_id == customer.id
    assert booking.id is not None


def test_gdpr_delete_works_with_future_booking(db):
    """Applies regardless of booking status — not blocked by an upcoming appointment."""
    tenant_id, biz = _setup(db)
    svc = create_service(db, tenant_id=tenant_id, business_id=biz.id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000004")
    create_booking(
        db,
        tenant_id=tenant_id,
        business_id=biz.id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=datetime.now(timezone.utc) + timedelta(days=30),
    )

    anonymized = gdpr_delete_customer(db, customer.id, tenant_id)

    assert anonymized.phone == "deleted"


def test_gdpr_delete_emits_audit_log(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000005")

    gdpr_delete_customer(db, customer.id, tenant_id, actor_id=None)

    logs = get_audit_logs(db, tenant_id, action=AuditAction.CUSTOMER_ANONYMIZED)
    entry = next((log for log in logs if log.source == f"customer_id={customer.id}"), None)
    assert entry is not None


# --- API ---

def _setup_admin_with_business(db, client, email: str) -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "API GDPR Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def test_api_gdpr_delete(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "gdpr-api1@example.com")
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    customer = get_or_create_customer(
        db, tenant_id=tenant.id, business_id=biz_id, phone="+48740000006", name="Real Name"
    )

    response = client.post(
        f"/api/v1/businesses/{biz_id}/customers/{customer.id}/gdpr-delete",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] is None
    assert data["phone"] == "deleted"


def test_api_gdpr_delete_requires_admin(db, client):
    register_user(client, "gdpr-member@example.com")
    token = login_user(client, "gdpr-member@example.com").json()["access_token"]
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48740000007")

    response = client.post(
        f"/api/v1/businesses/{biz.id}/customers/{customer.id}/gdpr-delete",
        headers=auth_headers(token),
    )

    assert response.status_code == 403
