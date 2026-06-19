"""P2-001: CRM clients table.

A Client is a business-managed profile (name/email/phone/notes), distinct
from the lightweight Customer row created automatically at booking time.
Optionally linked to a Customer via customer_id.
"""
import uuid

from app.core.domain_errors import ConflictError, NotFoundError
from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.client_service import (
    create_client,
    get_client,
    list_clients,
    require_client,
    update_client,
)
from app.services.customer_service import get_or_create_customer
from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _setup(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Client Salon", timezone="UTC")
    return tenant.id, biz


def _create_second_tenant(db):
    slug = f"other-biz-{uuid.uuid4().hex[:8]}"
    tenant = Tenant(slug=slug, name="Other Biz", is_active=True)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


def test_create_client_minimal(db):
    tenant_id, biz = _setup(db)

    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Jane Doe")

    assert client_row.id is not None
    assert client_row.business_id == biz.id
    assert client_row.customer_id is None
    assert client_row.email is None


def test_create_client_linked_to_customer(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48700100200")

    client_row = create_client(
        db, tenant_id=tenant_id, business_id=biz.id, name="Jane Doe", customer_id=customer.id,
        email="jane@example.com",
    )

    assert client_row.customer_id == customer.id
    assert client_row.email == "jane@example.com"


def test_create_client_duplicate_customer_link_raises(db):
    tenant_id, biz = _setup(db)
    customer = get_or_create_customer(db, tenant_id=tenant_id, business_id=biz.id, phone="+48700100201")
    create_client(db, tenant_id=tenant_id, business_id=biz.id, name="First", customer_id=customer.id)

    try:
        create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Second", customer_id=customer.id)
        raise AssertionError("expected ConflictError")
    except ConflictError:
        pass


def test_get_client_returns_none_for_other_tenant(db):
    tenant_id, biz = _setup(db)
    other_tenant = _create_second_tenant(db)
    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Jane Doe")

    assert get_client(db, client_row.id, other_tenant.id) is None
    assert get_client(db, client_row.id, tenant_id) is not None


def test_require_client_raises_not_found(db):
    tenant_id, _biz = _setup(db)

    try:
        require_client(db, 999999, tenant_id)
        raise AssertionError("expected NotFoundError")
    except NotFoundError:
        pass


def test_list_clients_scoped_to_business(db):
    tenant_id, biz = _setup(db)
    other_biz = create_business(db, tenant_id=tenant_id, name="Other Salon", timezone="UTC")
    create_client(db, tenant_id=tenant_id, business_id=biz.id, name="In Scope")
    create_client(db, tenant_id=tenant_id, business_id=other_biz.id, name="Out Of Scope")

    clients = list_clients(db, biz.id, tenant_id)

    names = {c.name for c in clients}
    assert "In Scope" in names
    assert "Out Of Scope" not in names


def test_update_client_changes_fields(db):
    tenant_id, biz = _setup(db)
    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Jane")

    updated = update_client(db, client_row.id, biz.id, tenant_id, notes="VIP customer")

    assert updated.notes == "VIP customer"
    assert updated.name == "Jane"


# --- API ---

def _setup_admin_with_business(db, client, email: str) -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "API Client Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def test_api_create_and_get_client(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "client-api1@example.com")

    create_resp = client.post(
        f"/api/v1/businesses/{biz_id}/clients",
        json={"name": "Anna Nowak", "email": "anna@example.com"},
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == "Anna Nowak"

    get_resp = client.get(
        f"/api/v1/businesses/{biz_id}/clients/{created['id']}",
        headers=auth_headers(token),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["email"] == "anna@example.com"


def test_api_list_clients(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "client-api2@example.com")
    client.post(
        f"/api/v1/businesses/{biz_id}/clients",
        json={"name": "Listed Client"},
        headers=auth_headers(token),
    )

    response = client.get(f"/api/v1/businesses/{biz_id}/clients", headers=auth_headers(token))

    assert response.status_code == 200
    assert any(c["name"] == "Listed Client" for c in response.json())


def test_api_update_client_requires_admin(db, client):
    register_user(client, "client-member@example.com")
    token = login_user(client, "client-member@example.com").json()["access_token"]
    tenant_id, biz = _setup(db)
    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Jane")

    response = client.patch(
        f"/api/v1/businesses/{biz.id}/clients/{client_row.id}",
        json={"notes": "hack"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_client_not_visible_across_tenants(db):
    tenant_id, biz = _setup(db)
    other_tenant = _create_second_tenant(db)
    client_row = create_client(db, tenant_id=tenant_id, business_id=biz.id, name="Tenant A Client")

    assert get_client(db, client_row.id, other_tenant.id) is None
