"""Tests for AVS-I001 transfer hours: CRUD, validation, tenant isolation."""
import pytest

from app.models.tenant import Tenant
from app.services.business_service import create_business
from app.services.business_transfer_hours_service import (
    create_transfer_hours,
    get_transfer_hours,
    list_transfer_hours,
)
from tests.database import auth_headers, login_user, promote_to_admin, register_user


@pytest.fixture()
def domain(db, client):
    register_user(client, "th_admin@example.com")
    promote_to_admin(db, "th_admin@example.com")
    token = login_user(client, "th_admin@example.com").json()["access_token"]
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    biz = create_business(db, tenant_id=tenant.id, name="Transfer Hours Salon", timezone="UTC")
    return {
        "client": client,
        "headers": auth_headers(token),
        "tenant_id": tenant.id,
        "business_id": biz.id,
        "db": db,
    }


# ---------------------------------------------------------------------------
# API: create
# ---------------------------------------------------------------------------

def test_create_transfer_hours(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["day_of_week"] == 0
    assert data["start_time"] == "09:00:00"
    assert data["end_time"] == "17:00:00"
    assert data["business_id"] == biz_id


def test_create_requires_admin(domain):
    client, biz_id = domain["client"], domain["business_id"]
    register_user(client, "th_nonadmin@example.com")
    token = login_user(client, "th_nonadmin@example.com").json()["access_token"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# API: list
# ---------------------------------------------------------------------------

def test_list_transfer_hours_empty(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.get(f"/api/v1/businesses/{biz_id}/transfer-hours", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_transfer_hours_ordered(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 2, "start_time": "10:00:00", "end_time": "14:00:00"},
        headers=headers,
    )
    client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    resp = client.get(f"/api/v1/businesses/{biz_id}/transfer-hours", headers=headers)
    assert resp.status_code == 200
    days = [r["day_of_week"] for r in resp.json()]
    assert days == sorted(days)


# ---------------------------------------------------------------------------
# API: get by id
# ---------------------------------------------------------------------------

def test_get_transfer_hours_not_found(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.get(f"/api/v1/businesses/{biz_id}/transfer-hours/99999", headers=headers)
    assert resp.status_code == 404


def test_get_transfer_hours_wrong_business_returns_404(domain, db):
    """Entry belongs to biz A; fetching under biz B must return 404, not the record."""
    client, headers = domain["client"], domain["headers"]
    biz_a_id = domain["business_id"]
    tenant_id = domain["tenant_id"]

    biz_b = create_business(db, tenant_id=tenant_id, name="Other Biz", timezone="UTC")

    entry_id = client.post(
        f"/api/v1/businesses/{biz_a_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    ).json()["id"]

    resp = client.get(f"/api/v1/businesses/{biz_b.id}/transfer-hours/{entry_id}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# API: delete
# ---------------------------------------------------------------------------

def test_delete_transfer_hours(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    entry_id = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 1, "start_time": "08:00:00", "end_time": "12:00:00"},
        headers=headers,
    ).json()["id"]

    resp = client.delete(f"/api/v1/businesses/{biz_id}/transfer-hours/{entry_id}", headers=headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/businesses/{biz_id}/transfer-hours", headers=headers)
    assert resp.json() == []


def test_delete_wrong_business_returns_404(domain, db):
    """DELETE on an entry from another business within the same tenant must return 404."""
    client, headers = domain["client"], domain["headers"]
    biz_a_id = domain["business_id"]
    tenant_id = domain["tenant_id"]

    biz_b = create_business(db, tenant_id=tenant_id, name="Other Biz B", timezone="UTC")

    entry_id = client.post(
        f"/api/v1/businesses/{biz_a_id}/transfer-hours",
        json={"day_of_week": 2, "start_time": "10:00:00", "end_time": "12:00:00"},
        headers=headers,
    ).json()["id"]

    resp = client.delete(f"/api/v1/businesses/{biz_b.id}/transfer-hours/{entry_id}", headers=headers)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_end_time_must_be_after_start_time(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "17:00:00", "end_time": "09:00:00"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_equal_start_end_time_rejected(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "10:00:00", "end_time": "10:00:00"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_invalid_day_of_week_rejected(domain):
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 7, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_duplicate_start_time_rejected(domain):
    """Two windows for the same business/day/start_time must be rejected (UniqueConstraint)."""
    client, headers, biz_id = domain["client"], domain["headers"], domain["business_id"]
    client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "12:00:00"},
        headers=headers,
    )
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Service-layer tenant isolation
# ---------------------------------------------------------------------------

def test_service_list_is_tenant_scoped(db, domain):
    tenant_id, biz_id = domain["tenant_id"], domain["business_id"]
    create_transfer_hours(
        db, tenant_id=tenant_id, business_id=biz_id,
        day_of_week=0, start_time=__import__("datetime").time(9), end_time=__import__("datetime").time(17),
    )
    results_correct = list_transfer_hours(db, biz_id, tenant_id)
    results_wrong = list_transfer_hours(db, biz_id, tenant_id + 9999)
    assert len(results_correct) == 1
    assert len(results_wrong) == 0


def test_service_get_enforces_tenant_id(db, domain):
    from datetime import time
    tenant_id, biz_id = domain["tenant_id"], domain["business_id"]
    entry = create_transfer_hours(
        db, tenant_id=tenant_id, business_id=biz_id,
        day_of_week=1, start_time=time(8), end_time=time(12),
    )
    assert get_transfer_hours(db, entry.id, tenant_id, biz_id) is not None
    assert get_transfer_hours(db, entry.id, tenant_id + 9999, biz_id) is None


def test_service_get_enforces_business_id(db, domain):
    from datetime import time
    tenant_id, biz_id = domain["tenant_id"], domain["business_id"]
    entry = create_transfer_hours(
        db, tenant_id=tenant_id, business_id=biz_id,
        day_of_week=2, start_time=time(10), end_time=time(14),
    )
    assert get_transfer_hours(db, entry.id, tenant_id, biz_id) is not None
    assert get_transfer_hours(db, entry.id, tenant_id, biz_id + 9999) is None
