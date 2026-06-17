"""AVS-L004: Self-service onboarding API.

Tests cover:
- POST /api/v1/onboarding: one-call atomic business setup
- DELETE /api/v1/businesses/{id}/services/{service_id}: service hard delete
- PATCH /api/v1/businesses/{id}/working-hours/{wh_id}: working hours update
"""
import pytest

from app.schemas.onboarding import OnboardingSetupRequest
from app.services.onboarding_service import setup_business_onboarding
from tests.database import auth_headers, login_user, promote_to_admin, register_user


_ONBOARDING_URL = "/api/v1/onboarding"

_FULL_SETUP = {
    "business": {
        "name": "Test Onboarding Salon",
        "timezone": "Europe/Warsaw",
        "phone": "+48100200300",
        "booking_mode": "internal_booking",
    },
    "staff": [
        {"name": "Anna", "phone": "+48111000111"},
        {"name": "Bartek"},
    ],
    "services": [
        {"name": "Haircut", "duration_minutes": 30, "price_minor_units": 5000, "currency": "PLN"},
        {"name": "Coloring", "duration_minutes": 90},
    ],
    "working_hours": [
        {"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"},
        {"day_of_week": 1, "start_time": "10:00", "end_time": "18:00"},
    ],
}


@pytest.fixture()
def admin(db, client):
    register_user(client, "l004_admin@example.com")
    promote_to_admin(db, "l004_admin@example.com")
    token = login_user(client, "l004_admin@example.com").json()["access_token"]
    return {"client": client, "headers": auth_headers(token), "db": db}


# ---------------------------------------------------------------------------
# Schema validation (unit)
# ---------------------------------------------------------------------------

def test_onboarding_schema_valid_internal():
    req = OnboardingSetupRequest(**_FULL_SETUP)
    assert req.business.booking_mode == "internal_booking"
    assert len(req.staff) == 2
    assert len(req.services) == 2
    assert len(req.working_hours) == 2


def test_onboarding_schema_external_requires_url():
    with pytest.raises(ValueError, match="external_booking_url is required"):
        OnboardingSetupRequest(
            business={
                "name": "Salon",
                "timezone": "Europe/Warsaw",
                "booking_mode": "external_booking_link",
            },
            staff=[],
            services=[],
            working_hours=[],
        )


def test_onboarding_schema_external_mode_valid():
    req = OnboardingSetupRequest(
        business={
            "name": "Booksy Salon",
            "timezone": "Europe/Warsaw",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/pl-pl/salon",
        },
    )
    assert req.business.external_booking_url == "https://booksy.com/pl-pl/salon"


def test_onboarding_schema_working_hours_end_after_start():
    with pytest.raises(ValueError, match="end_time must be after start_time"):
        OnboardingSetupRequest(
            business={"name": "Salon", "timezone": "Europe/Warsaw"},
            working_hours=[{"day_of_week": 0, "start_time": "17:00", "end_time": "09:00"}],
        )


def test_onboarding_schema_empty_lists_allowed():
    req = OnboardingSetupRequest(
        business={"name": "Minimal Salon", "timezone": "Europe/Warsaw"},
    )
    assert req.staff == []
    assert req.services == []
    assert req.working_hours == []


# ---------------------------------------------------------------------------
# Service (unit)
# ---------------------------------------------------------------------------

def test_onboarding_service_creates_business_and_entities(db):
    from app.models.business import Business
    from app.models.service import Service
    from app.models.staff import Staff
    from app.models.working_hours import WorkingHours

    req = OnboardingSetupRequest(**_FULL_SETUP)
    # use tenant_id=1 (default tenant from seed)
    resp = setup_business_onboarding(db, tenant_id=1, request=req)

    assert resp.business_id is not None
    assert resp.staff_count == 2
    assert resp.service_count == 2
    assert resp.working_hours_count == 2

    business = db.query(Business).filter(Business.id == resp.business_id).first()
    assert business is not None
    assert business.name == "Test Onboarding Salon"

    assert db.query(Staff).filter(Staff.business_id == resp.business_id).count() == 2
    assert db.query(Service).filter(Service.business_id == resp.business_id).count() == 2
    assert db.query(WorkingHours).filter(WorkingHours.business_id == resp.business_id).count() == 2


# ---------------------------------------------------------------------------
# POST /api/v1/onboarding
# ---------------------------------------------------------------------------

def test_onboarding_endpoint_full_setup(admin, client):
    resp = client.post(_ONBOARDING_URL, json=_FULL_SETUP, headers=admin["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Test Onboarding Salon"
    assert data["staff_count"] == 2
    assert data["service_count"] == 2
    assert data["working_hours_count"] == 2
    assert "business_id" in data


def test_onboarding_endpoint_external_mode(admin, client):
    payload = {
        "business": {
            "name": "Booksy Salon",
            "timezone": "Europe/Warsaw",
            "booking_mode": "external_booking_link",
            "external_booking_url": "https://booksy.com/pl-pl/salon",
        },
    }
    resp = client.post(_ONBOARDING_URL, json=payload, headers=admin["headers"])
    assert resp.status_code == 201
    data = resp.json()
    assert data["staff_count"] == 0
    assert data["service_count"] == 0


def test_onboarding_endpoint_external_mode_missing_url_rejected(admin, client):
    payload = {
        "business": {
            "name": "Bad Salon",
            "timezone": "Europe/Warsaw",
            "booking_mode": "external_booking_link",
        },
    }
    resp = client.post(_ONBOARDING_URL, json=payload, headers=admin["headers"])
    assert resp.status_code == 422


def test_onboarding_endpoint_missing_business_rejected(admin, client):
    resp = client.post(_ONBOARDING_URL, json={}, headers=admin["headers"])
    assert resp.status_code == 422


def test_onboarding_endpoint_requires_auth(client):
    resp = client.post(_ONBOARDING_URL, json=_FULL_SETUP)
    assert resp.status_code == 401


def test_onboarding_endpoint_requires_admin(client):
    register_user(client, "l004_nonadmin@example.com")
    token = login_user(client, "l004_nonadmin@example.com").json()["access_token"]
    resp = client.post(_ONBOARDING_URL, json=_FULL_SETUP, headers=auth_headers(token))
    assert resp.status_code == 403


def test_onboarding_endpoint_business_exists_in_db(admin, client, db):
    from app.models.business import Business

    resp = client.post(_ONBOARDING_URL, json=_FULL_SETUP, headers=admin["headers"])
    biz_id = resp.json()["business_id"]
    biz = db.query(Business).filter(Business.id == biz_id).first()
    assert biz is not None
    assert biz.booking_mode == "internal_booking"


def test_onboarding_endpoint_empty_staff_and_services(admin, client):
    payload = {
        "business": {"name": "Solo Salon", "timezone": "Europe/Warsaw"},
        "staff": [],
        "services": [],
        "working_hours": [],
    }
    resp = client.post(_ONBOARDING_URL, json=payload, headers=admin["headers"])
    assert resp.status_code == 201
    assert resp.json()["staff_count"] == 0


# ---------------------------------------------------------------------------
# DELETE /api/v1/businesses/{id}/services/{service_id}
# ---------------------------------------------------------------------------

def test_service_delete_removes_service(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "Delete Test Salon", "timezone": "Europe/Warsaw"},
        "services": [{"name": "Test Service", "duration_minutes": 30}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    services_resp = client.get(
        f"/api/v1/businesses/{biz_id}/services",
        headers=admin["headers"],
    )
    service_id = services_resp.json()[0]["id"]

    del_resp = client.delete(
        f"/api/v1/businesses/{biz_id}/services/{service_id}",
        headers=admin["headers"],
    )
    assert del_resp.status_code == 204

    services_after = client.get(
        f"/api/v1/businesses/{biz_id}/services",
        headers=admin["headers"],
    )
    assert all(s["id"] != service_id for s in services_after.json())


def test_service_delete_missing_returns_404(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "404 Salon", "timezone": "Europe/Warsaw"},
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    resp = client.delete(
        f"/api/v1/businesses/{biz_id}/services/999999",
        headers=admin["headers"],
    )
    assert resp.status_code == 404


def test_service_delete_requires_admin(admin, client, db):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "Auth Test Salon", "timezone": "Europe/Warsaw"},
        "services": [{"name": "Svc", "duration_minutes": 15}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]
    svc_id = client.get(
        f"/api/v1/businesses/{biz_id}/services", headers=admin["headers"]
    ).json()[0]["id"]

    register_user(client, "l004_del_nonadmin@example.com")
    token = login_user(client, "l004_del_nonadmin@example.com").json()["access_token"]
    resp = client.delete(
        f"/api/v1/businesses/{biz_id}/services/{svc_id}",
        headers=auth_headers(token),
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# PATCH /api/v1/businesses/{id}/working-hours/{wh_id}
# ---------------------------------------------------------------------------

def test_working_hours_patch_updates_times(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "WH Patch Salon", "timezone": "Europe/Warsaw"},
        "working_hours": [{"day_of_week": 2, "start_time": "09:00", "end_time": "17:00"}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    wh_id = client.get(
        f"/api/v1/businesses/{biz_id}/working-hours", headers=admin["headers"]
    ).json()[0]["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/working-hours/{wh_id}",
        json={"start_time": "10:00", "end_time": "18:00"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["start_time"] == "10:00:00"
    assert resp.json()["end_time"] == "18:00:00"


def test_working_hours_patch_partial_update(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "WH Partial Salon", "timezone": "Europe/Warsaw"},
        "working_hours": [{"day_of_week": 3, "start_time": "08:00", "end_time": "16:00"}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    wh_id = client.get(
        f"/api/v1/businesses/{biz_id}/working-hours", headers=admin["headers"]
    ).json()[0]["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/working-hours/{wh_id}",
        json={"end_time": "20:00"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["start_time"] == "08:00:00"
    assert resp.json()["end_time"] == "20:00:00"


def test_working_hours_patch_invalid_range_rejected(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "WH Bad Range Salon", "timezone": "Europe/Warsaw"},
        "working_hours": [{"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    wh_id = client.get(
        f"/api/v1/businesses/{biz_id}/working-hours", headers=admin["headers"]
    ).json()[0]["id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/working-hours/{wh_id}",
        json={"start_time": "17:00", "end_time": "09:00"},
        headers=admin["headers"],
    )
    assert resp.status_code == 422


def test_working_hours_patch_missing_returns_404(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "WH 404 Salon", "timezone": "Europe/Warsaw"},
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/working-hours/999999",
        json={"end_time": "18:00"},
        headers=admin["headers"],
    )
    assert resp.status_code == 404


def test_working_hours_patch_requires_admin(admin, client):
    biz_resp = client.post(_ONBOARDING_URL, json={
        "business": {"name": "WH Auth Salon", "timezone": "Europe/Warsaw"},
        "working_hours": [{"day_of_week": 5, "start_time": "09:00", "end_time": "13:00"}],
    }, headers=admin["headers"])
    biz_id = biz_resp.json()["business_id"]

    wh_id = client.get(
        f"/api/v1/businesses/{biz_id}/working-hours", headers=admin["headers"]
    ).json()[0]["id"]

    register_user(client, "l004_wh_nonadmin@example.com")
    token = login_user(client, "l004_wh_nonadmin@example.com").json()["access_token"]
    resp = client.patch(
        f"/api/v1/businesses/{biz_id}/working-hours/{wh_id}",
        json={"end_time": "15:00"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403
