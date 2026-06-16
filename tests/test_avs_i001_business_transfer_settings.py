"""Tests for AVS-I001: business transfer settings."""
import pytest

from app.models.business import TransferDestinationPolicy
from app.models.tenant import Tenant
from app.services.business_service import create_business, get_business, update_business
from tests.database import auth_headers, login_user, promote_to_admin, register_user


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def admin(db, client):
    register_user(client, "i001_admin@example.com")
    promote_to_admin(db, "i001_admin@example.com")
    token = login_user(client, "i001_admin@example.com").json()["access_token"]
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    return {
        "client": client,
        "headers": auth_headers(token),
        "tenant_id": tenant.id,
        "db": db,
    }


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------

def test_transfer_disabled_by_default(admin, db):
    biz = create_business(db, tenant_id=admin["tenant_id"], name="Default Salon", timezone="UTC")
    assert biz.transfer_enabled is False
    assert biz.transfer_destination_policy == TransferDestinationPolicy.BUSINESS_PHONE


def test_transfer_destination_policy_enum_values():
    assert TransferDestinationPolicy.BUSINESS_PHONE == "business_phone"
    assert TransferDestinationPolicy.STAFF == "staff"


# ---------------------------------------------------------------------------
# API: GET returns transfer fields
# ---------------------------------------------------------------------------

def test_get_business_returns_transfer_fields(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={"name": "Read Test Salon", "timezone": "UTC"},
        headers=headers,
    )
    assert resp.status_code == 201
    biz_id = resp.json()["id"]

    resp = client.get(f"/api/v1/businesses/{biz_id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["transfer_enabled"] is False
    assert data["transfer_destination_policy"] == "business_phone"


# ---------------------------------------------------------------------------
# API: POST create with transfer settings
# ---------------------------------------------------------------------------

def test_create_business_with_transfer_enabled(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Transfer Salon",
            "timezone": "UTC",
            "transfer_enabled": True,
            "transfer_destination_policy": "business_phone",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["transfer_enabled"] is True
    assert data["transfer_destination_policy"] == "business_phone"


def test_create_business_with_staff_policy(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Staff Policy Salon",
            "timezone": "UTC",
            "transfer_enabled": True,
            "transfer_destination_policy": "staff",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["transfer_destination_policy"] == "staff"


def test_create_business_rejects_invalid_policy(admin):
    client, headers = admin["client"], admin["headers"]
    resp = client.post(
        "/api/v1/businesses",
        json={
            "name": "Bad Policy Salon",
            "timezone": "UTC",
            "transfer_destination_policy": "invalid_policy",
        },
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# API: PATCH update transfer settings
# ---------------------------------------------------------------------------

def test_update_enables_transfer(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Update Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"transfer_enabled": True},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["transfer_enabled"] is True
    assert resp.json()["transfer_destination_policy"] == "business_phone"


def test_update_changes_policy(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Policy Switch Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"transfer_destination_policy": "staff"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["transfer_destination_policy"] == "staff"


def test_update_rejects_invalid_policy(admin):
    client, headers = admin["client"], admin["headers"]
    biz_id = client.post(
        "/api/v1/businesses",
        json={"name": "Bad Update Salon", "timezone": "UTC"},
        headers=headers,
    ).json()["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"transfer_destination_policy": "unknown"},
        headers=headers,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------
# The test environment has only one tenant ("default"). A genuine HTTP
# cross-tenant test is not possible here without provisioning a second tenant.
# Tenant isolation for transfer settings is verified at the service layer:
# both get_business() and update_business() filter by tenant_id, so a request
# with a wrong tenant_id cannot read or mutate another tenant's business.

def test_service_get_enforces_tenant_id(db, admin):
    biz = create_business(db, tenant_id=admin["tenant_id"], name="Scoped Salon", timezone="UTC",
                          transfer_enabled=True)
    found = get_business(db, biz.id, tenant_id=admin["tenant_id"])
    wrong_tenant = get_business(db, biz.id, tenant_id=admin["tenant_id"] + 9999)
    assert found is not None
    assert found.transfer_enabled is True
    assert wrong_tenant is None


def test_service_update_enforces_tenant_id(db, admin):
    from app.core.domain_errors import NotFoundError
    biz = create_business(db, tenant_id=admin["tenant_id"], name="Guard Salon", timezone="UTC")
    with pytest.raises(NotFoundError):
        update_business(db, biz.id, tenant_id=admin["tenant_id"] + 9999, transfer_enabled=True)
    # original record must be unchanged
    unchanged = get_business(db, biz.id, tenant_id=admin["tenant_id"])
    assert unchanged is not None
    assert unchanged.transfer_enabled is False


def test_service_create_scopes_to_given_tenant(db, admin):
    biz = create_business(db, tenant_id=admin["tenant_id"], name="Tenanted Salon", timezone="UTC",
                          transfer_enabled=True, transfer_destination_policy="staff")
    assert get_business(db, biz.id, tenant_id=admin["tenant_id"]) is not None
    assert get_business(db, biz.id, tenant_id=admin["tenant_id"] + 1) is None
