from app.models.tenant import Tenant
from app.models.user import User


def ensure_tenant(db, slug: str, name: str) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == slug).first()

    if tenant is None:
        tenant = Tenant(slug=slug, name=name, is_active=True)
        db.add(tenant)
        db.commit()
        db.refresh(tenant)

    return tenant


def restore_default_tenant(db) -> None:
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    tenant.is_active = True
    db.commit()


def register_user(client, email: str, password: str = "password123", tenant_slug: str | None = None):
    headers = {}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug

    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
        headers=headers,
    )


def login_user(client, email: str, password: str = "password123", tenant_slug: str | None = None):
    headers = {}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug

    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )


def auth_headers(access_token: str, tenant_slug: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug
    return headers


def promote_to_admin(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).one()
    user.role = "admin"
    db.commit()
    db.refresh(user)
    return user


def promote_to_platform_admin(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).one()
    user.role = "platform_admin"
    db.commit()
    db.refresh(user)
    return user


def test_authenticated_request_rejects_mismatched_tenant_header(db, client):
    register_user(client, "member@example.com")
    login_response = login_user(client, "member@example.com")
    access_token = login_response.json()["access_token"]

    ensure_tenant(db, "acme", "Acme Corp")

    response = client.get(
        "/auth/me",
        headers=auth_headers(access_token, tenant_slug="acme"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Tenant access denied"


def test_authenticated_request_allows_matching_tenant_header(client):
    register_user(client, "member@example.com")
    login_response = login_user(client, "member@example.com")
    access_token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers=auth_headers(access_token, tenant_slug="default"),
    )

    assert response.status_code == 200
    assert response.json()["email"] == "member@example.com"


def test_inactive_tenant_blocks_authenticated_access(db, client):
    register_user(client, "inactive-user@example.com")
    login_response = login_user(client, "inactive-user@example.com")
    access_token = login_response.json()["access_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    tenant.is_active = False
    db.commit()

    try:
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 403
        assert response.json()["error"]["message"] == "Tenant access denied"
    finally:
        restore_default_tenant(db)


def test_inactive_tenant_blocks_refresh_token(db, client):
    register_user(client, "refresh-user@example.com")
    login_response = login_user(client, "refresh-user@example.com")
    refresh_token = login_response.json()["refresh_token"]

    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    tenant.is_active = False
    db.commit()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 403
        assert response.json()["error"]["message"] == "Tenant access denied"
    finally:
        restore_default_tenant(db)


def test_admin_cannot_read_user_from_other_tenant(db, client):
    ensure_tenant(db, "acme", "Acme Corp")

    register_user(client, "admin@example.com")
    promote_to_admin(db, "admin@example.com")
    admin_login = login_user(client, "admin@example.com")
    admin_token = admin_login.json()["access_token"]

    other_tenant_user = register_user(
        client,
        "acme-user@example.com",
        tenant_slug="acme",
    )
    other_user_id = other_tenant_user.json()["id"]

    response = client.get(
        f"/users/{other_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404


def test_platform_admin_can_provision_tenant(db, client):
    register_user(client, "platform-admin@example.com")
    promote_to_platform_admin(db, "platform-admin@example.com")
    admin_login = login_user(client, "platform-admin@example.com")
    admin_token = admin_login.json()["access_token"]

    response = client.post(
        "/admin/tenants",
        json={"slug": "northwind-isolation", "name": "Northwind Traders"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "northwind-isolation"

    tenant = db.query(Tenant).filter(Tenant.slug == "northwind-isolation").one()
    assert tenant.is_active is True


def test_regular_user_cannot_provision_tenant(client):
    register_user(client, "regular-user@example.com")
    login_response = login_user(client, "regular-user@example.com")
    access_token = login_response.json()["access_token"]

    response = client.post(
        "/admin/tenants",
        json={"slug": "blocked", "name": "Blocked Tenant"},
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 403


def test_platform_admin_can_deactivate_tenant(db, client):
    register_user(client, "lifecycle-admin@example.com")
    promote_to_platform_admin(db, "lifecycle-admin@example.com")
    admin_login = login_user(client, "lifecycle-admin@example.com")
    admin_token = admin_login.json()["access_token"]

    create_response = client.post(
        "/admin/tenants",
        json={"slug": "sunset-isolation", "name": "Sunset Corp"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    tenant_id = create_response.json()["id"]

    register_user(client, "sunset-user@example.com", tenant_slug="sunset-isolation")

    deactivate_response = client.patch(
        f"/admin/tenants/{tenant_id}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["is_active"] is False

    login_response = login_user(
        client,
        "sunset-user@example.com",
        tenant_slug="sunset-isolation",
    )
    assert login_response.status_code == 404


def test_tenant_admin_cannot_provision_tenant(db, client):
    ensure_tenant(db, "acme", "Acme Corp")

    register_user(client, "acme-admin@example.com", tenant_slug="acme")
    promote_to_admin(db, "acme-admin@example.com")
    admin_login = login_user(client, "acme-admin@example.com", tenant_slug="acme")
    admin_token = admin_login.json()["access_token"]

    response = client.post(
        "/admin/tenants",
        json={"slug": "blocked-by-tenant-admin", "name": "Blocked Tenant"},
        headers=auth_headers(admin_token, tenant_slug="acme"),
    )

    assert response.status_code == 403


def test_tenant_admin_cannot_list_or_manage_tenants(db, client):
    ensure_tenant(db, "acme", "Acme Corp")

    register_user(client, "acme-admin@example.com", tenant_slug="acme")
    promote_to_admin(db, "acme-admin@example.com")
    admin_login = login_user(client, "acme-admin@example.com", tenant_slug="acme")
    admin_token = admin_login.json()["access_token"]
    headers = auth_headers(admin_token, tenant_slug="acme")

    list_response = client.get("/admin/tenants", headers=headers)
    assert list_response.status_code == 403

    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()
    read_response = client.get(
        f"/admin/tenants/{default_tenant.id}",
        headers=headers,
    )
    assert read_response.status_code == 403

    patch_response = client.patch(
        f"/admin/tenants/{default_tenant.id}",
        json={"name": "Renamed Default"},
        headers=headers,
    )
    assert patch_response.status_code == 403


def test_tenant_admin_can_manage_users_in_own_tenant(db, client):
    ensure_tenant(db, "acme", "Acme Corp")

    register_user(client, "acme-admin@example.com", tenant_slug="acme")
    promote_to_admin(db, "acme-admin@example.com")
    admin_login = login_user(client, "acme-admin@example.com", tenant_slug="acme")
    admin_token = admin_login.json()["access_token"]
    headers = auth_headers(admin_token, tenant_slug="acme")

    member_response = register_user(
        client,
        "acme-member@example.com",
        tenant_slug="acme",
    )
    member_id = member_response.json()["id"]

    list_response = client.get("/users/", headers=headers)
    assert list_response.status_code == 200

    read_response = client.get(f"/users/{member_id}", headers=headers)
    assert read_response.status_code == 200
    assert read_response.json()["email"] == "acme-member@example.com"
