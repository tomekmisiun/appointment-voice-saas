"""P2-004: client booking history API.

GET /businesses/{business_id}/clients/{client_id}/bookings exposes
get_bookings_for_client() (P2-002) over HTTP.
"""
from datetime import datetime, timedelta, timezone

from app.models.tenant import Tenant
from app.services.booking_service import create_booking
from app.services.client_service import create_client
from app.services.customer_service import get_or_create_customer
from app.services.service_service import create_service
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _setup_admin_with_business(db, client, email: str) -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "History API Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def test_api_get_client_bookings(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "history-api1@example.com")
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    svc = create_service(db, tenant_id=tenant.id, business_id=biz_id, name="Cut", duration_minutes=30)
    customer = get_or_create_customer(db, tenant_id=tenant.id, business_id=biz_id, phone="+48730000001")
    client_row = create_client(
        db, tenant_id=tenant.id, business_id=biz_id, name="Jane", customer_id=customer.id
    )
    starts_at = datetime.now(timezone.utc) + timedelta(days=5)
    booking = create_booking(
        db,
        tenant_id=tenant.id,
        business_id=biz_id,
        customer_id=customer.id,
        service_id=svc.id,
        staff_id=None,
        starts_at=starts_at,
    )

    response = client.get(
        f"/api/v1/businesses/{biz_id}/clients/{client_row.id}/bookings",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == booking.id


def test_api_get_client_bookings_empty_without_linked_customer(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "history-api2@example.com")
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    client_row = create_client(db, tenant_id=tenant.id, business_id=biz_id, name="No Customer")

    response = client.get(
        f"/api/v1/businesses/{biz_id}/clients/{client_row.id}/bookings",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_api_get_client_bookings_unknown_client_returns_404(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "history-api3@example.com")

    response = client.get(
        f"/api/v1/businesses/{biz_id}/clients/999999/bookings",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
