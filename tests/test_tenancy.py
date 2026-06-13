from app.models.tenant import Tenant
from app.models.user import User
from app.services.tenant_service import build_tenant_cache_prefix, build_tenant_object_key_prefix


def test_default_tenant_exists_after_migrations(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").one()

    assert tenant.is_active is True
    assert tenant.name == "Default Tenant"


def test_register_assigns_default_tenant(db, client):
    response = client.post(
        "/auth/register",
        json={
            "email": "tenant-user@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 200

    user = db.query(User).filter(User.email == "tenant-user@example.com").one()
    tenant = db.query(Tenant).filter(Tenant.id == user.tenant_id).one()

    assert tenant.slug == "default"


def test_same_email_can_exist_in_different_tenants(db, client):
    second_tenant = Tenant(slug="acme", name="Acme Corp", is_active=True)
    db.add(second_tenant)
    db.commit()

    first_response = client.post(
        "/auth/register",
        json={
            "email": "shared@example.com",
            "password": "password123",
        },
    )
    second_response = client.post(
        "/auth/register",
        json={
            "email": "shared@example.com",
            "password": "password123",
        },
        headers={"X-Tenant-Slug": "acme"},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    users = db.query(User).filter(User.email == "shared@example.com").all()
    default_tenant = db.query(Tenant).filter(Tenant.slug == "default").one()

    assert len(users) == 2
    assert {user.tenant_id for user in users} == {default_tenant.id, second_tenant.id}


def test_tenant_cache_prefix_is_namespaced():
    assert build_tenant_cache_prefix(7) == "tenant:7"


def test_tenant_object_key_prefix_is_namespaced():
    assert build_tenant_object_key_prefix(7) == "tenants/7"
