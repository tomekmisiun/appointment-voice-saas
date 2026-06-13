from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse
from types import SimpleNamespace

from app.core.ids import uuid7
from app.core.security import hash_password_reset_token, verify_password
from app.models.audit_log import AuditAction, AuditLog
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services.email_templates import build_password_reset_url
from app.services.password_reset_service import (
    cleanup_expired_password_reset_tokens,
    create_password_reset_token_and_send_email,
)


class FakeEmailService:
    def __init__(self):
        self.sent_password_reset_emails = []

    def send_password_reset_email(self, recipient: str, raw_token: str) -> None:
        self.sent_password_reset_emails.append(
            {
                "recipient": recipient,
                "raw_token": raw_token,
                "reset_url": f"https://example.com/reset?token={raw_token}",
            }
        )


def deactivate_user_by_email(db, email: str) -> None:
    user = db.query(User).filter(User.email == email).first()
    user.is_active = False
    db.commit()


def create_reset_token_for_user(db, email: str, email_service: FakeEmailService) -> str:
    user = db.query(User).filter(User.email == email).one()

    create_password_reset_token_and_send_email(db, user.id)

    return email_service.sent_password_reset_emails[-1]["raw_token"]


def test_register(client):
    response = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True


def test_register_returns_403_when_registration_disabled(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.auth.settings.registration_policy", "disabled")

    response = client.post(
        "/auth/register",
        json={
            "email": "disabled-register@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Registration is disabled"


def test_register_duplicate_email(client):
    payload = {
        "email": "test@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=payload)
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 400


def test_login(client):
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_me(client):
    client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    login_response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123",
        },
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True


def test_me_unauthorized(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_refresh_token(client):
    register_data = {
        "email": "test@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


def test_refresh_rotates_refresh_token(client):
    register_data = {
        "email": "rotation@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    original_refresh_token = login_response.json()["refresh_token"]

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )

    assert refresh_response.status_code == 200

    rotated_refresh_token = refresh_response.json()["refresh_token"]

    assert rotated_refresh_token != original_refresh_token

    reuse_response = client.post(
        "/auth/refresh",
        json={"refresh_token": original_refresh_token},
    )

    assert reuse_response.status_code == 401

    rotated_response = client.post(
        "/auth/refresh",
        json={"refresh_token": rotated_refresh_token},
    )

    assert rotated_response.status_code == 200


def test_logout_revokes_refresh_token(client):
    register_data = {
        "email": "logout@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    refresh_token = login_response.json()["refresh_token"]

    logout_response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert logout_response.status_code == 204

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 401


def test_inactive_user_cannot_login(db, client):
    register_data = {
        "email": "inactive-login@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)
    deactivate_user_by_email(db, register_data["email"])

    response = client.post(
        "/auth/login",
        json=register_data,
    )

    assert response.status_code == 401


def test_inactive_user_cannot_use_access_token(db, client):
    register_data = {
        "email": "inactive-access@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    access_token = login_response.json()["access_token"]
    deactivate_user_by_email(db, register_data["email"])

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401


def test_inactive_user_cannot_refresh_token(db, client):
    register_data = {
        "email": "inactive-refresh@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    refresh_token = login_response.json()["refresh_token"]
    deactivate_user_by_email(db, register_data["email"])

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


def test_refresh_with_access_token(client):
    register_data = {
        "email": "test2@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=register_data)

    login_response = client.post(
        "/auth/login",
        json=register_data,
    )

    access_token = login_response.json()["access_token"]

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


def test_refresh_with_invalid_token(client):
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401


def test_password_reset_request_for_active_user_enqueues_email_job(
    db,
    client,
    monkeypatch,
):
    enqueued_jobs = []

    def fake_enqueue_job(job_type: str, payload: dict):
        enqueued_jobs.append({"type": job_type, "payload": payload})
        return SimpleNamespace(id="job-id")

    monkeypatch.setattr("app.services.password_reset_service.enqueue_job", fake_enqueue_job)
    register_data = {
        "email": "reset-active@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    token_count_before = db.query(PasswordResetToken).count()

    response = client.post(
        "/auth/password-reset/request",
        json={"email": register_data["email"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an account exists for this email, password reset instructions "
            "were sent."
        )
    }

    user = db.query(User).filter(User.email == register_data["email"]).one()

    assert enqueued_jobs == [
        {
            "type": "send_password_reset_email",
            "payload": {"user_id": user.id},
        }
    ]
    assert db.query(PasswordResetToken).count() == token_count_before


def test_password_reset_request_is_rate_limited(client):
    email = f"rate-limit-reset-{uuid7().hex}@example.com"

    responses = [
        client.post(
            "/auth/password-reset/request",
            json={"email": email},
        )
        for _ in range(4)
    ]

    assert [response.status_code for response in responses] == [200, 200, 200, 429]


def test_password_reset_request_creates_audit_log(db, client, monkeypatch):
    monkeypatch.setattr(
        "app.services.password_reset_service.enqueue_job",
        lambda job_type, payload: SimpleNamespace(id="job-id"),
    )
    register_data = {
        "email": "reset-request-audit@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)

    response = client.post(
        "/auth/password-reset/request",
        json={"email": register_data["email"]},
    )

    user = db.query(User).filter(User.email == register_data["email"]).one()
    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == AuditAction.PASSWORD_RESET_REQUESTED.value)
        .filter(AuditLog.target_user_id == user.id)
        .one()
    )

    assert response.status_code == 200
    assert audit_log.admin_id is None


def test_password_reset_request_for_missing_user_does_not_leak_account_status(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    token_count_before = db.query(PasswordResetToken).count()

    response = client.post(
        "/auth/password-reset/request",
        json={"email": "missing-reset@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an account exists for this email, password reset instructions "
            "were sent."
        )
    }
    assert db.query(PasswordResetToken).count() == token_count_before
    assert email_service.sent_password_reset_emails == []


def test_password_reset_request_for_inactive_user_does_not_leak_account_status(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-inactive@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    deactivate_user_by_email(db, register_data["email"])

    token_count_before = db.query(PasswordResetToken).count()

    response = client.post(
        "/auth/password-reset/request",
        json={"email": register_data["email"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            "If an account exists for this email, password reset instructions "
            "were sent."
        )
    }
    assert db.query(PasswordResetToken).count() == token_count_before
    assert email_service.sent_password_reset_emails == []


def test_password_reset_confirm_updates_password_and_marks_token_used(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-confirm@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    raw_token = create_reset_token_for_user(
        db,
        register_data["email"],
        email_service,
    )

    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )

    assert response.status_code == 200
    assert response.json() == {"message": "Password has been reset."}

    user = db.query(User).filter(User.email == register_data["email"]).one()
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .one()
    )

    assert reset_token.used_at is not None
    assert verify_password("new-password123", user.hashed_password)

    old_login_response = client.post(
        "/auth/login",
        json=register_data,
    )
    new_login_response = client.post(
        "/auth/login",
        json={
            "email": register_data["email"],
            "password": "new-password123",
        },
    )

    assert old_login_response.status_code == 401
    assert new_login_response.status_code == 200


def test_password_reset_confirm_creates_audit_log(db, client, monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-confirm-audit@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    raw_token = create_reset_token_for_user(
        db,
        register_data["email"],
        email_service,
    )

    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )

    user = db.query(User).filter(User.email == register_data["email"]).one()
    audit_log = (
        db.query(AuditLog)
        .filter(AuditLog.action == AuditAction.PASSWORD_RESET_CONFIRMED.value)
        .filter(AuditLog.target_user_id == user.id)
        .one()
    )

    assert response.status_code == 200
    assert audit_log.admin_id is None


def test_password_reset_confirm_rejects_invalid_token(client):
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": "invalid-token", "new_password": "new-password123"},
    )

    assert response.status_code == 400


def test_password_reset_confirm_rejects_expired_token(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-expired@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    raw_token = create_reset_token_for_user(
        db,
        register_data["email"],
        email_service,
    )
    user = db.query(User).filter(User.email == register_data["email"]).one()
    reset_token = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.user_id == user.id)
        .one()
    )
    reset_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )

    assert response.status_code == 400


def test_password_reset_confirm_rejects_reused_token(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-reused@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    raw_token = create_reset_token_for_user(
        db,
        register_data["email"],
        email_service,
    )

    first_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )
    second_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "another-password123"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_password_reset_confirm_rejects_inactive_user(
    db,
    client,
    monkeypatch,
):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-confirm-inactive@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    raw_token = create_reset_token_for_user(
        db,
        register_data["email"],
        email_service,
    )
    deactivate_user_by_email(db, register_data["email"])

    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )

    assert response.status_code == 400


def test_password_reset_email_reset_url_contains_valid_token(db, client, monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )
    register_data = {
        "email": "reset-url@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    create_reset_token_for_user(db, register_data["email"], email_service)

    reset_url = email_service.sent_password_reset_emails[0]["reset_url"]
    token = parse_qs(urlparse(reset_url).query)["token"][0]
    response = client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "new-password123"},
    )

    assert response.status_code == 200


def test_password_reset_url_is_built_from_configured_base_url():
    reset_url = build_password_reset_url(
        "https://app.example.com/reset-password",
        "raw-token",
    )

    parsed_url = urlparse(reset_url)

    assert reset_url.startswith("https://app.example.com/reset-password?")
    assert parse_qs(parsed_url.query)["token"] == ["raw-token"]


def test_cleanup_expired_password_reset_tokens_removes_only_expired_tokens(
    db,
    client,
):
    register_data = {
        "email": "reset-cleanup@example.com",
        "password": "password123",
    }
    client.post("/auth/register", json=register_data)
    user = db.query(User).filter(User.email == register_data["email"]).one()
    expired_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token("expired-token"),
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    active_token = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_password_reset_token("active-token"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    db.add(expired_token)
    db.add(active_token)
    db.commit()

    deleted_count = cleanup_expired_password_reset_tokens(db)

    remaining_tokens = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id
    )

    assert deleted_count >= 1
    assert remaining_tokens.count() == 1
    assert remaining_tokens.one().token_hash == active_token.token_hash
