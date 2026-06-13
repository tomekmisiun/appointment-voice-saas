from tests.test_auth import FakeEmailService, create_reset_token_for_user
from tests.test_users import auth_headers, create_user_and_login, make_admin


def test_access_token_invalid_after_password_reset(db, client, monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    email = "revoke-reset@example.com"
    access_token, _user_id = create_user_and_login(db, client, email)
    raw_token = create_reset_token_for_user(db, email, email_service)

    confirm_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )
    assert confirm_response.status_code == 200

    me_response = client.get("/auth/me", headers=auth_headers(access_token))
    assert me_response.status_code == 401

    new_login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "new-password123"},
    )
    assert new_login_response.status_code == 200


def test_refresh_token_invalid_after_password_reset(db, client, monkeypatch):
    email_service = FakeEmailService()
    monkeypatch.setattr(
        "app.services.password_reset_service.get_email_service",
        lambda: email_service,
    )

    email = "revoke-refresh-reset@example.com"
    _access_token, _user_id = create_user_and_login(db, client, email)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]
    raw_token = create_reset_token_for_user(db, email, email_service)

    confirm_response = client.post(
        "/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "new-password123"},
    )
    assert confirm_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_access_token_invalid_after_user_deactivation(db, client):
    email = "revoke-deactivate@example.com"
    user_token, user_id = create_user_and_login(db, client, email)
    admin_email = "revoke-deactivate-admin@example.com"
    admin_token, _admin_id = create_user_and_login(db, client, admin_email)
    make_admin(db, admin_email)

    deactivate_response = client.patch(
        f"/users/{user_id}/deactivate",
        headers=auth_headers(admin_token),
    )
    assert deactivate_response.status_code == 200

    me_response = client.get("/auth/me", headers=auth_headers(user_token))
    assert me_response.status_code == 401


def test_refresh_token_invalid_after_user_deactivation(db, client):
    email = "revoke-refresh-deactivate@example.com"
    _user_token, user_id = create_user_and_login(db, client, email)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]
    admin_email = "revoke-refresh-deactivate-admin@example.com"
    admin_token, _admin_id = create_user_and_login(db, client, admin_email)
    make_admin(db, admin_email)

    deactivate_response = client.patch(
        f"/users/{user_id}/deactivate",
        headers=auth_headers(admin_token),
    )
    assert deactivate_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401


def test_access_token_invalid_after_role_change(db, client):
    email = "revoke-role@example.com"
    user_token, user_id = create_user_and_login(db, client, email)
    admin_email = "revoke-role-admin@example.com"
    admin_token, _admin_id = create_user_and_login(db, client, admin_email)
    make_admin(db, admin_email)

    update_response = client.patch(
        f"/users/{user_id}",
        json={"role": "admin"},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200

    me_response = client.get("/auth/me", headers=auth_headers(user_token))
    assert me_response.status_code == 401

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert login_response.status_code == 200


def test_refresh_token_invalid_after_role_change(db, client):
    email = "revoke-refresh-role@example.com"
    _user_token, user_id = create_user_and_login(db, client, email)
    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": "password123"},
    )
    refresh_token = login_response.json()["refresh_token"]
    admin_email = "revoke-refresh-role-admin@example.com"
    admin_token, _admin_id = create_user_and_login(db, client, admin_email)
    make_admin(db, admin_email)

    update_response = client.patch(
        f"/users/{user_id}",
        json={"role": "admin"},
        headers=auth_headers(admin_token),
    )
    assert update_response.status_code == 200

    refresh_response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 401
