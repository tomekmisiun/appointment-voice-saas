"""P4-004: self-service salon signup.

POST /api/v1/signup creates a brand new tenant, first business, and first
admin user in one public, unauthenticated call. Deliberately separate from
POST /admin/tenants (provision_tenant()), which is for an already-onboarded
platform admin to create *another* tenant, not for the public to create
their first one.
"""
from app.models.audit_log import AuditAction, AuditLog
from app.models.business import Business
from app.models.tenant import Tenant
from app.models.user import User
from tests.database import auth_headers, login_user


def test_signup_creates_tenant_and_admin_user(db, client):
    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Glamour Studio",
            "admin_email": "owner_signup1@example.com",
            "admin_password": "strong-password-123",
        },
    )

    assert resp.status_code == 201
    data = resp.json()
    assert data["tenant"]["slug"] == "glamour-studio"
    assert data["tenant"]["name"] == "Glamour Studio"
    assert data["tenant"]["is_active"] is True
    assert data["user"]["email"] == "owner_signup1@example.com"
    assert data["user"]["role"] == "admin"

    tenant = db.query(Tenant).filter(Tenant.slug == "glamour-studio").one()
    user = db.query(User).filter(User.email == "owner_signup1@example.com").one()
    business = db.query(Business).filter(Business.tenant_id == tenant.id).one()
    assert user.tenant_id == tenant.id
    assert user.role == "admin"
    assert business.name == "Glamour Studio"
    assert business.timezone == "Europe/Warsaw"
    assert business.is_active is True


def test_signup_with_explicit_slug(db, client):
    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Custom Slug Salon",
            "slug": "my-custom-slug",
            "admin_email": "owner_signup2@example.com",
            "admin_password": "strong-password-123",
        },
    )

    assert resp.status_code == 201
    assert resp.json()["tenant"]["slug"] == "my-custom-slug"


def test_signup_rejects_duplicate_explicit_slug(client):
    body = {
        "salon_name": "Dup Salon",
        "slug": "dup-salon-slug",
        "admin_password": "strong-password-123",
    }
    first = client.post("/api/v1/signup", json={**body, "admin_email": "dup1@example.com"})
    assert first.status_code == 201

    second = client.post("/api/v1/signup", json={**body, "admin_email": "dup2@example.com"})
    assert second.status_code == 400


def test_signup_auto_generates_unique_slug_on_name_collision(client):
    body = {"salon_name": "Collision Salon", "admin_password": "strong-password-123"}
    first = client.post("/api/v1/signup", json={**body, "admin_email": "collide1@example.com"})
    second = client.post("/api/v1/signup", json={**body, "admin_email": "collide2@example.com"})

    assert first.status_code == 201
    assert second.status_code == 201
    slug1 = first.json()["tenant"]["slug"]
    slug2 = second.json()["tenant"]["slug"]
    assert slug1 != slug2
    assert slug1 == "collision-salon"
    assert slug2 == "collision-salon-2"


def test_signup_rejects_weak_password(client):
    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Weak Pw Salon",
            "admin_email": "weakpw@example.com",
            "admin_password": "short",
        },
    )
    assert resp.status_code == 422


def test_signup_rejects_invalid_slug_format(client):
    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Bad Slug Salon",
            "slug": "Not Valid Slug!",
            "admin_email": "badslug@example.com",
            "admin_password": "strong-password-123",
        },
    )
    assert resp.status_code == 422


def test_signup_logs_self_signup_audit_action(db, client):
    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Audit Salon",
            "admin_email": "audit_signup@example.com",
            "admin_password": "strong-password-123",
        },
    )
    tenant_id = resp.json()["tenant"]["id"]

    log = (
        db.query(AuditLog)
        .filter(AuditLog.tenant_id == tenant_id, AuditLog.action == AuditAction.TENANT_CREATED)
        .one()
    )
    assert log.admin_id is None
    assert log.source == "self_signup"


def test_signup_admin_can_log_in_and_see_their_business(client):
    signup_resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "End To End Salon",
            "admin_email": "e2e_owner@example.com",
            "admin_password": "strong-password-123",
        },
    )
    slug = signup_resp.json()["tenant"]["slug"]

    login_resp = login_user(
        client, "e2e_owner@example.com", "strong-password-123", tenant_slug=slug
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    list_resp = client.get(
        "/api/v1/businesses",
        headers=auth_headers(token, tenant_slug=slug),
    )
    assert list_resp.status_code == 200
    businesses = list_resp.json()
    assert len(businesses) == 1
    assert businesses[0]["name"] == "End To End Salon"


def test_signup_onboarding_reuses_initial_business(client):
    signup_resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Reuse Salon",
            "admin_email": "reuse_owner@example.com",
            "admin_password": "strong-password-123",
        },
    )
    slug = signup_resp.json()["tenant"]["slug"]

    token = login_user(
        client, "reuse_owner@example.com", "strong-password-123", tenant_slug=slug
    ).json()["access_token"]
    headers = auth_headers(token, tenant_slug=slug)

    onboarding_resp = client.post(
        "/api/v1/onboarding",
        json={
            "business": {"name": "Configured Reuse Salon", "timezone": "Europe/London"},
            "staff": [{"name": "Alex"}],
            "services": [{"name": "Haircut", "duration_minutes": 30}],
            "working_hours": [{"day_of_week": 0, "start_time": "09:00", "end_time": "17:00"}],
        },
        headers=headers,
    )

    assert onboarding_resp.status_code == 201
    businesses_resp = client.get("/api/v1/businesses", headers=headers)
    assert businesses_resp.status_code == 200
    businesses = businesses_resp.json()
    assert len(businesses) == 1
    assert businesses[0]["id"] == onboarding_resp.json()["business_id"]
    assert businesses[0]["name"] == "Configured Reuse Salon"
    assert businesses[0]["timezone"] == "Europe/London"


def test_signup_disabled_returns_403(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.signup.settings.registration_policy", "disabled")

    resp = client.post(
        "/api/v1/signup",
        json={
            "salon_name": "Disabled Salon",
            "admin_email": "disabled_signup@example.com",
            "admin_password": "strong-password-123",
        },
    )
    assert resp.status_code == 403
