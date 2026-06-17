"""AVS-L001: Owner lead intake — public submission + admin management.

OwnerLead is not tenant-scoped: leads represent prospective new tenants.
Public endpoint is rate-limited; admin endpoints require auth + admin role.
"""
import pytest

from app.models.owner_lead import LeadBookingModeInterest, LeadStatus, OwnerLead
from app.schemas.owner_lead import OwnerLeadCreate
from app.services.owner_lead_service import create_owner_lead, get_owner_lead
from tests.database import auth_headers, login_user, promote_to_admin, register_user


URL = "/api/v1/owner-leads"

_VALID_PAYLOAD = {
    "business_name": "Salon Anna",
    "owner_name": "Anna Kowalska",
    "email": "anna@example.com",
    "phone_number": "+48123123123",
    "city": "Gdańsk",
    "booking_mode_interest": "external_booking_link",
    "external_booking_url": "https://booksy.com/pl-pl/salon-anna",
    "message": "Chcę przetestować IVR po godzinach.",
}


@pytest.fixture()
def admin(db, client):
    register_user(client, "l001_admin@example.com")
    promote_to_admin(db, "l001_admin@example.com")
    token = login_user(client, "l001_admin@example.com").json()["access_token"]
    return {"client": client, "headers": auth_headers(token), "db": db}


# ---------------------------------------------------------------------------
# Schema validation (unit)
# ---------------------------------------------------------------------------

def test_schema_valid_external_lead():
    schema = OwnerLeadCreate(**_VALID_PAYLOAD)
    assert schema.booking_mode_interest == LeadBookingModeInterest.EXTERNAL_BOOKING_LINK
    assert schema.external_booking_url == "https://booksy.com/pl-pl/salon-anna"


def test_schema_external_link_requires_url():
    with pytest.raises(ValueError, match="external_booking_url is required"):
        OwnerLeadCreate(
            business_name="Salon",
            email="a@b.com",
            phone_number="+48111222333",
            booking_mode_interest="external_booking_link",
        )


def test_schema_standalone_booking_no_url_required():
    schema = OwnerLeadCreate(
        business_name="Salon",
        email="a@b.com",
        phone_number="+48111222333",
        booking_mode_interest="standalone_booking",
    )
    assert schema.external_booking_url is None


def test_schema_unsure_no_url_required():
    schema = OwnerLeadCreate(
        business_name="Salon",
        email="a@b.com",
        phone_number="+48111222333",
        booking_mode_interest="unsure",
    )
    assert schema.booking_mode_interest == LeadBookingModeInterest.UNSURE


def test_schema_rejects_non_http_url():
    with pytest.raises(ValueError, match="http"):
        OwnerLeadCreate(
            business_name="Salon",
            email="a@b.com",
            phone_number="+48111222333",
            booking_mode_interest="external_booking_link",
            external_booking_url="javascript:alert(1)",
        )


def test_schema_rejects_newline_in_url():
    with pytest.raises(ValueError, match="newline"):
        OwnerLeadCreate(
            business_name="Salon",
            email="a@b.com",
            phone_number="+48111222333",
            booking_mode_interest="external_booking_link",
            external_booking_url="https://booksy.com/123\ninjected",
        )


def test_schema_rejects_invalid_email():
    with pytest.raises(ValueError):
        OwnerLeadCreate(
            business_name="Salon",
            email="not-an-email",
            phone_number="+48111222333",
            booking_mode_interest="standalone_booking",
        )


def test_schema_message_max_length():
    with pytest.raises(ValueError):
        OwnerLeadCreate(
            business_name="Salon",
            email="a@b.com",
            phone_number="+48111222333",
            booking_mode_interest="standalone_booking",
            message="x" * 1001,
        )


# ---------------------------------------------------------------------------
# Service (unit)
# ---------------------------------------------------------------------------

def test_service_creates_lead(db):
    lead = create_owner_lead(
        db,
        business_name="Test Salon",
        owner_name="Jan",
        email="JAN@EXAMPLE.COM",
        phone_number="+48 600 100 200",
        city="Warsaw",
        booking_mode_interest="standalone_booking",
        external_booking_url=None,
        message="Hello",
    )
    assert lead.id is not None
    assert lead.status == LeadStatus.NEW
    assert lead.email == "jan@example.com"
    assert lead.phone_normalized == "+48600100200"


def test_service_get_owner_lead(db):
    lead = create_owner_lead(
        db,
        business_name="GetMe Salon",
        owner_name=None,
        email="x@y.com",
        phone_number="+48999000111",
        city=None,
        booking_mode_interest="unsure",
        external_booking_url=None,
        message=None,
    )
    fetched = get_owner_lead(db, lead.id)
    assert fetched is not None
    assert fetched.business_name == "GetMe Salon"


def test_service_get_owner_lead_not_found(db):
    assert get_owner_lead(db, 999999) is None


# ---------------------------------------------------------------------------
# Public API: POST /api/v1/owner-leads
# ---------------------------------------------------------------------------

def test_public_submit_valid_lead(client):
    resp = client.post(URL, json=_VALID_PAYLOAD)
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Salon Anna"
    assert data["status"] == "new"
    assert data["booking_mode_interest"] == "external_booking_link"
    assert "id" in data
    assert "created_at" in data


def test_public_submit_standalone_mode(client):
    resp = client.post(URL, json={
        "business_name": "Barber Mike",
        "email": "mike@example.com",
        "phone_number": "+48500600700",
        "booking_mode_interest": "standalone_booking",
    })
    assert resp.status_code == 201
    assert resp.json()["booking_mode_interest"] == "standalone_booking"


def test_public_submit_returns_only_public_fields(client):
    resp = client.post(URL, json=_VALID_PAYLOAD)
    data = resp.json()
    assert "email" not in data
    assert "phone_number" not in data
    assert "phone_normalized" not in data
    assert "message" not in data
    assert "owner_name" not in data


def test_public_submit_missing_business_name_rejected(client):
    payload = {**_VALID_PAYLOAD, "business_name": ""}
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_public_submit_missing_email_rejected(client):
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "email"}
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_public_submit_invalid_email_rejected(client):
    resp = client.post(URL, json={**_VALID_PAYLOAD, "email": "not-an-email"})
    assert resp.status_code == 422


def test_public_submit_missing_phone_rejected(client):
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "phone_number"}
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_public_submit_invalid_booking_mode_rejected(client):
    resp = client.post(URL, json={**_VALID_PAYLOAD, "booking_mode_interest": "unknown_mode"})
    assert resp.status_code == 422


def test_public_submit_external_link_mode_requires_url(client):
    payload = {**_VALID_PAYLOAD}
    del payload["external_booking_url"]
    resp = client.post(URL, json=payload)
    assert resp.status_code == 422


def test_public_submit_non_http_url_rejected(client):
    resp = client.post(URL, json={**_VALID_PAYLOAD, "external_booking_url": "ftp://bad.url/x"})
    assert resp.status_code == 422


def test_public_submit_requires_no_auth(client):
    resp = client.post(URL, json=_VALID_PAYLOAD)
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Admin API: GET /api/v1/owner-leads
# ---------------------------------------------------------------------------

def test_admin_can_list_leads(admin, client):
    client.post(URL, json=_VALID_PAYLOAD)
    resp = client.get(URL, headers=admin["headers"])
    assert resp.status_code == 200
    leads = resp.json()
    assert isinstance(leads, list)
    assert any(lead["business_name"] == "Salon Anna" for lead in leads)


def test_admin_list_includes_full_fields(admin, client):
    client.post(URL, json=_VALID_PAYLOAD)
    resp = client.get(URL, headers=admin["headers"])
    first = resp.json()[0]
    assert "email" in first
    assert "phone_number" in first
    assert "message" in first


def test_admin_list_filter_by_status(admin, db, client):
    create_owner_lead(
        db,
        business_name="Status Filter Salon",
        owner_name=None,
        email="sf@example.com",
        phone_number="+48111000111",
        city=None,
        booking_mode_interest="standalone_booking",
        external_booking_url=None,
        message=None,
    )
    resp = client.get(f"{URL}?status=new", headers=admin["headers"])
    assert resp.status_code == 200
    names = [lead["business_name"] for lead in resp.json()]
    assert "Status Filter Salon" in names

    resp2 = client.get(f"{URL}?status=contacted", headers=admin["headers"])
    names2 = [lead["business_name"] for lead in resp2.json()]
    assert "Status Filter Salon" not in names2


def test_admin_get_single_lead(admin, client):
    post_resp = client.post(URL, json=_VALID_PAYLOAD)
    lead_id = post_resp.json()["id"]
    resp = client.get(f"{URL}/{lead_id}", headers=admin["headers"])
    assert resp.status_code == 200
    assert resp.json()["id"] == lead_id
    assert resp.json()["email"] == "anna@example.com"


def test_admin_get_missing_lead_returns_404(admin, client):
    resp = client.get(f"{URL}/999999", headers=admin["headers"])
    assert resp.status_code == 404


def test_admin_list_requires_auth(client):
    resp = client.get(URL)
    assert resp.status_code == 401


def test_non_admin_cannot_list_leads(client):
    register_user(client, "l001_nonadmin@example.com")
    token = login_user(client, "l001_nonadmin@example.com").json()["access_token"]
    resp = client.get(URL, headers=auth_headers(token))
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Admin API: PATCH /api/v1/owner-leads/{id}/status
# ---------------------------------------------------------------------------

def test_admin_can_update_lead_status(admin, client):
    post_resp = client.post(URL, json=_VALID_PAYLOAD)
    lead_id = post_resp.json()["id"]

    resp = client.patch(
        f"{URL}/{lead_id}/status",
        json={"status": "contacted"},
        headers=admin["headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "contacted"


def test_admin_status_update_all_valid_values(admin, client):
    for new_status in ("contacted", "qualified", "onboarded", "rejected", "new"):
        post_resp = client.post(URL, json={**_VALID_PAYLOAD, "business_name": f"Salon {new_status}"})
        lead_id = post_resp.json()["id"]
        resp = client.patch(
            f"{URL}/{lead_id}/status",
            json={"status": new_status},
            headers=admin["headers"],
        )
        assert resp.status_code == 200, f"failed for status={new_status}"
        assert resp.json()["status"] == new_status


def test_admin_status_update_invalid_value_rejected(admin, client):
    post_resp = client.post(URL, json=_VALID_PAYLOAD)
    lead_id = post_resp.json()["id"]
    resp = client.patch(
        f"{URL}/{lead_id}/status",
        json={"status": "unknown_status"},
        headers=admin["headers"],
    )
    assert resp.status_code == 422


def test_admin_status_update_missing_lead_returns_404(admin, client):
    resp = client.patch(
        f"{URL}/999999/status",
        json={"status": "contacted"},
        headers=admin["headers"],
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Status default
# ---------------------------------------------------------------------------

def test_default_status_is_new(client, db):
    client.post(URL, json=_VALID_PAYLOAD)
    lead = db.query(OwnerLead).order_by(OwnerLead.id.desc()).first()
    assert lead is not None
    assert lead.status == "new"


# ---------------------------------------------------------------------------
# Phone normalization
# ---------------------------------------------------------------------------

def test_phone_normalized_on_create(client, db):
    client.post(URL, json={**_VALID_PAYLOAD, "phone_number": "+48 600-100 200"})
    lead = db.query(OwnerLead).order_by(OwnerLead.id.desc()).first()
    assert lead is not None
    assert lead.phone_normalized == "+48600100200"
    assert lead.phone_number == "+48 600-100 200"
