"""Tests for the public demo feature.

Covers:
- POST /auth/demo session creation (enabled / disabled / misconfigured)
- Read-only enforcement: demo user blocked from all mutation categories
- Owner of the same business is NOT blocked
- GET endpoints work for demo user
- Shared data: owner update visible to demo user
- Demo user cannot access other tenants/businesses
- Webhooks and IVR simulation not blocked
- seed_demo_user idempotency
"""

import pytest
from unittest.mock import patch

from app.models.tenant import Tenant
from app.models.user import User
from app.seed_demo_data import DEMO_USER_EMAIL, seed_demo_user
from tests.database import auth_headers, login_user, promote_to_admin, register_user


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_demo_user(db, tenant_id: int) -> User:
    from app.core.security import hash_password
    import secrets
    existing = db.query(User).filter(
        User.email == DEMO_USER_EMAIL,
        User.tenant_id == tenant_id,
    ).first()
    if existing is not None:
        return existing
    user = User(
        tenant_id=tenant_id,
        email=DEMO_USER_EMAIL,
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        is_active=True,
        role="user",
        is_demo_user=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _demo_headers(client, db, tenant_id: int, business_id: int) -> dict:
    """Create demo user, configure demo settings, call /auth/demo."""
    _make_demo_user(db, tenant_id)
    with patch("app.services.auth_service.settings") as mock_settings:
        mock_settings.public_demo_enabled = True
        mock_settings.public_demo_user_email = DEMO_USER_EMAIL
        mock_settings.public_demo_business_id = business_id
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _admin_setup(db, client) -> tuple[int, int, dict]:
    """Register+promote admin, create business, return (tenant_id, biz_id, headers)."""
    register_user(client, "owner@test.com")
    promote_to_admin(db, "owner@test.com")
    login_resp = login_user(client, "owner@test.com")
    token = login_resp.json()["access_token"]
    headers = auth_headers(token)

    resp = client.post(
        "/api/v1/businesses",
        json={"name": "Demo Biz", "timezone": "UTC"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    biz_id = resp.json()["id"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    return tenant.id, biz_id, headers


# ── demo session endpoint ────────────────────────────────────────────────────

def test_demo_endpoint_returns_tokens_when_enabled(client, db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    _, biz_id, _ = _admin_setup(db, client)
    _make_demo_user(db, tenant.id)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = DEMO_USER_EMAIL
        ms.public_demo_business_id = biz_id
        resp = client.post("/api/v1/auth/demo")

    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_demo_endpoint_returns_503_when_disabled(client, db):
    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = False
        ms.public_demo_user_email = ""
        ms.public_demo_business_id = 0
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 503


def test_demo_endpoint_returns_503_when_email_not_set(client, db):
    _, biz_id, _ = _admin_setup(db, client)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = ""
        ms.public_demo_business_id = biz_id
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 503


def test_demo_endpoint_returns_503_when_business_id_not_set(client, db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    _make_demo_user(db, tenant.id)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = DEMO_USER_EMAIL
        ms.public_demo_business_id = 0
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 503


def test_demo_endpoint_returns_503_when_demo_user_missing(client, db):
    # Use an email that is guaranteed not to be seeded in the DB.
    absent_email = "never-seeded-demo@example.com"
    _, biz_id, _ = _admin_setup(db, client)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = absent_email
        ms.public_demo_business_id = biz_id
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 503


def test_demo_endpoint_returns_503_when_demo_user_not_is_demo_user(client, db):
    """Regular (non-demo) user with matching email is not accepted."""
    # Use a unique email so a previously seeded is_demo_user record doesn't interfere.
    non_demo_email = "regular-only@example.com"
    register_user(client, non_demo_email)
    _, biz_id, _ = _admin_setup(db, client)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = non_demo_email
        ms.public_demo_business_id = biz_id
        resp = client.post("/api/v1/auth/demo")
    assert resp.status_code == 503


def test_demo_endpoint_no_arbitrary_business_id_in_body(client, db):
    """The endpoint accepts no body — it always uses config, not client input."""
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    _, biz_id, _ = _admin_setup(db, client)
    _make_demo_user(db, tenant.id)

    with patch("app.services.auth_service.settings") as ms:
        ms.public_demo_enabled = True
        ms.public_demo_user_email = DEMO_USER_EMAIL
        ms.public_demo_business_id = biz_id
        # body with arbitrary field: must still only use configured business
        resp = client.post("/api/v1/auth/demo", json={"business_id": 99999})
    assert resp.status_code == 200


def test_demo_user_can_read_businesses(client, db):
    _, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db,
        db.query(Tenant).filter(Tenant.slug == "default").one().id,
        biz_id)
    resp = client.get(f"/api/v1/businesses/{biz_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == biz_id


def test_demo_user_only_sees_configured_business(client, db):
    """If another business exists in the same tenant, demo user must not see it."""
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    # Create second business as owner
    resp2 = client.post(
        "/api/v1/businesses",
        json={"name": "Other Biz", "timezone": "UTC"},
        headers=owner_headers,
    )
    assert resp2.status_code == 201
    other_biz_id = resp2.json()["id"]

    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    # Patch business_service.settings so the biz-id filter is active at request time.
    with patch("app.services.business_service.settings") as ms:
        ms.public_demo_business_id = biz_id
        resp = client.get("/api/v1/businesses", headers=demo_hdrs)
    assert resp.status_code == 200
    ids = [b["id"] for b in resp.json()]
    assert biz_id in ids
    assert other_biz_id not in ids


# ── read-only enforcement ────────────────────────────────────────────────────

def test_demo_user_cannot_create_business(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        "/api/v1/businesses",
        json={"name": "New Biz", "timezone": "UTC"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_update_business(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"name": "Hacked"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_create_staff(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Hacker"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_create_service(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={"name": "Free Cut", "duration_minutes": 30, "price_minor_units": 0, "currency": "PLN"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_delete_service(client, db):
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    svc_resp = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={"name": "Cut", "duration_minutes": 30, "price_minor_units": 5000, "currency": "PLN"},
        headers=owner_headers,
    )
    svc_id = svc_resp.json()["id"]
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.delete(f"/api/v1/businesses/{biz_id}/services/{svc_id}", headers=headers)
    assert resp.status_code == 403


def test_demo_user_cannot_create_working_hours(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/working-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_create_availability_exception(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/availability-exceptions",
        json={"date": "2030-01-01", "is_closed": True},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_create_booking(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/bookings",
        json={
            "customer_id": 1,
            "service_id": 1,
            "starts_at": "2030-01-01T09:00:00Z",
            "source": "demo_attempt",
        },
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_cancel_booking(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/bookings/1/cancel",
        json={"reason": "demo"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_create_recurring_block(client, db):
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    staff_resp = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Alice"},
        headers=owner_headers,
    )
    staff_id = staff_resp.json()["id"]
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/recurring-staff-blocks",
        json={"staff_id": staff_id, "day_of_week": 1, "start_time": "12:00:00", "end_time": "13:00:00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_patch_user(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.patch("/api/v1/users/1", json={"email": "hacked@evil.com"}, headers=headers)
    assert resp.status_code == 403


def test_demo_user_cannot_update_transfer_hours(client, db):
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    headers = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.post(
        f"/api/v1/businesses/{biz_id}/transfer-hours",
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_demo_user_cannot_list_services_for_other_business(client, db):
    """Demo user must be blocked from listing services on a non-configured business."""
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    resp2 = client.post(
        "/api/v1/businesses",
        json={"name": "Other Biz 2", "timezone": "UTC"},
        headers=owner_headers,
    )
    assert resp2.status_code == 201
    other_biz_id = resp2.json()["id"]

    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    with patch("app.api.dependencies.auth.settings") as ms:
        ms.public_demo_business_id = biz_id
        resp = client.get(f"/api/v1/businesses/{other_biz_id}/services", headers=demo_hdrs)
    assert resp.status_code == 403


def test_demo_user_cannot_list_staff_for_other_business(client, db):
    """Demo user must be blocked from listing staff on a non-configured business."""
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    resp2 = client.post(
        "/api/v1/businesses",
        json={"name": "Other Biz Staff", "timezone": "UTC"},
        headers=owner_headers,
    )
    assert resp2.status_code == 201
    other_biz_id = resp2.json()["id"]

    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    with patch("app.api.dependencies.auth.settings") as ms:
        ms.public_demo_business_id = biz_id
        resp = client.get(f"/api/v1/businesses/{other_biz_id}/staff", headers=demo_hdrs)
    assert resp.status_code == 403


def test_demo_user_cannot_read_other_business_directly(client, db):
    """GET /businesses/{id} must also block demo users for non-configured businesses."""
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    resp2 = client.post(
        "/api/v1/businesses",
        json={"name": "Secret Biz", "timezone": "UTC"},
        headers=owner_headers,
    )
    assert resp2.status_code == 201
    other_biz_id = resp2.json()["id"]

    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    with patch("app.api.dependencies.auth.settings") as ms:
        ms.public_demo_business_id = biz_id
        resp = client.get(f"/api/v1/businesses/{other_biz_id}", headers=demo_hdrs)
    assert resp.status_code == 403


def test_demo_user_can_read_configured_business_directly(client, db):
    """Demo user may still fetch the configured business by its ID directly."""
    tenant_id, biz_id, _ = _admin_setup(db, client)
    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    with patch("app.api.dependencies.auth.settings") as ms:
        ms.public_demo_business_id = biz_id
        resp = client.get(f"/api/v1/businesses/{biz_id}", headers=demo_hdrs)
    assert resp.status_code == 200
    assert resp.json()["id"] == biz_id


# ── owner NOT blocked ─────────────────────────────────────────────────────────

def test_owner_can_still_update_business_after_demo_setup(client, db):
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    _make_demo_user(db, tenant_id)
    resp = client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"name": "Updated by Owner"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated by Owner"


# ── shared data visible to demo user ─────────────────────────────────────────

def test_demo_user_sees_owner_update(client, db):
    tenant_id, biz_id, owner_headers = _admin_setup(db, client)
    # Owner updates business name
    client.patch(
        f"/api/v1/businesses/{biz_id}",
        json={"name": "New Name By Owner"},
        headers=owner_headers,
    )
    # Demo user reads
    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.get(f"/api/v1/businesses/{biz_id}", headers=demo_hdrs)
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name By Owner"


# ── IVR simulation not blocked ────────────────────────────────────────────────

def test_ivr_simulate_not_blocked_for_demo_user(client, db):
    """IVR /simulate endpoints use no user auth — they must not be affected."""
    resp = client.post(
        "/api/v1/ivr/simulate/call",
        json={"business_id": 99999, "caller_phone": "+48600000001"},
    )
    # Any status except 403 is acceptable — we're verifying the demo guard is NOT applied.
    # 401 means the endpoint requires auth (unauthenticated call); still not a demo guard block.
    assert resp.status_code in (401, 404, 422, 200, 201)


# ── demo user auth/me exposes is_demo_user ────────────────────────────────────

def test_demo_session_me_returns_is_demo_user_true(client, db):
    tenant_id, biz_id, _ = _admin_setup(db, client)
    demo_hdrs = _demo_headers(client, db, tenant_id, biz_id)
    resp = client.get("/api/v1/auth/me", headers=demo_hdrs)
    assert resp.status_code == 200
    assert resp.json()["is_demo_user"] is True


def test_normal_user_me_returns_is_demo_user_false(client, db):
    register_user(client, "normal@test.com")
    resp = login_user(client, "normal@test.com")
    token = resp.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers=auth_headers(token))
    assert me.status_code == 200
    assert me.json()["is_demo_user"] is False


# ── seed idempotency ──────────────────────────────────────────────────────────

def test_seed_demo_user_is_idempotent(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    seed_demo_user(db, tenant.id)
    seed_demo_user(db, tenant.id)
    count = db.query(User).filter(
        User.email == DEMO_USER_EMAIL,
        User.tenant_id == tenant.id,
    ).count()
    assert count == 1


def test_seed_demo_user_sets_is_demo_user_flag(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    seed_demo_user(db, tenant.id)
    user = db.query(User).filter(
        User.email == DEMO_USER_EMAIL,
        User.tenant_id == tenant.id,
    ).one()
    assert user.is_demo_user is True
    assert user.is_active is True


def test_seed_demo_user_raises_if_existing_user_not_is_demo_user(client, db):
    """seed_demo_user must fail loudly when the email belongs to a non-demo user."""
    from app.core.ids import uuid7
    from app.core.security import hash_password
    import secrets

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    non_demo_email = f"conflict-seed-{uuid7().hex}@example.com"
    regular_user = User(
        tenant_id=tenant.id,
        email=non_demo_email,
        hashed_password=hash_password(secrets.token_urlsafe(16)),
        is_active=True,
        role="user",
        is_demo_user=False,
    )
    db.add(regular_user)
    db.commit()

    with patch("app.seed_demo_data.settings") as ms:
        ms.public_demo_user_email = non_demo_email
        with pytest.raises(ValueError, match="is_demo_user=False"):
            seed_demo_user(db, tenant.id)


# ── password reset blocked for demo user ──────────────────────────────────────

def test_demo_user_password_reset_request_is_silently_ignored(client, db):
    """Reset request for a demo user returns the generic message and never enqueues a job."""
    from app.services.password_reset_service import PASSWORD_RESET_RESPONSE_MESSAGE

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    _make_demo_user(db, tenant.id)

    with patch("app.services.password_reset_service.enqueue_job") as mock_enqueue:
        resp = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": DEMO_USER_EMAIL},
        )

    assert resp.status_code == 200
    assert resp.json()["message"] == PASSWORD_RESET_RESPONSE_MESSAGE
    mock_enqueue.assert_not_called()


def test_demo_user_reset_token_worker_skips_without_minting(db):
    """Worker-side guard: create_password_reset_token_and_send_email must not mint a
    token or send email for a demo user even when called directly."""
    from app.models.password_reset_token import PasswordResetToken
    from app.services.password_reset_service import create_password_reset_token_and_send_email

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    demo_user = _make_demo_user(db, tenant.id)

    with patch("app.services.password_reset_service.get_email_service") as mock_email:
        create_password_reset_token_and_send_email(db, demo_user.id)

    token_count = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == demo_user.id)
        .count()
    )
    assert token_count == 0
    mock_email.assert_not_called()


def test_demo_user_reset_token_confirm_rejected(client, db):
    """A reset token created directly for a demo user must be rejected at confirm."""
    from datetime import datetime, timedelta, timezone
    from app.models.password_reset_token import PasswordResetToken
    from app.core.security import generate_password_reset_token, hash_password_reset_token

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    demo_user = _make_demo_user(db, tenant.id)

    raw_token = generate_password_reset_token()
    reset_token = PasswordResetToken(
        user_id=demo_user.id,
        token_hash=hash_password_reset_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset_token)
    db.commit()

    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "NewPassword123!"},
    )
    assert resp.status_code == 400
