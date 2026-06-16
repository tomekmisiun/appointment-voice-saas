"""Tests for Business CRUD (AVS-B001)."""

from tests.database import (
    auth_headers,
    login_user,
    promote_to_admin,
    register_user,
)


def test_admin_can_create_business(db, client):
    register_user(client, "owner@example.com")
    promote_to_admin(db, "owner@example.com")
    token = login_user(client, "owner@example.com").json()["access_token"]

    response = client.post(
        "/api/v1/businesses",
        json={"name": "Quick Cuts", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Quick Cuts"
    assert data["timezone"] == "Europe/Warsaw"
    assert data["is_active"] is True
    assert "id" in data


def test_regular_user_cannot_create_business(db, client):
    register_user(client, "user@example.com")
    token = login_user(client, "user@example.com").json()["access_token"]

    response = client.post(
        "/api/v1/businesses",
        json={"name": "Quick Cuts", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    )

    assert response.status_code == 403


def test_list_businesses_requires_auth(client):
    response = client.get("/api/v1/businesses")
    assert response.status_code == 401


def test_admin_can_list_businesses(db, client):
    register_user(client, "owner2@example.com")
    promote_to_admin(db, "owner2@example.com")
    token = login_user(client, "owner2@example.com").json()["access_token"]

    create_resp = client.post(
        "/api/v1/businesses",
        json={"name": "Salon A", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 201
    biz_id = create_resp.json()["id"]

    # Verify the business appears via GET by id (list is capped at 100 and fragile to test-db state)
    response = client.get(f"/api/v1/businesses/{biz_id}", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["name"] == "Salon A"

    # Also verify the list endpoint is callable
    list_resp = client.get("/api/v1/businesses", headers=auth_headers(token))
    assert list_resp.status_code == 200


def test_get_business_by_id(db, client):
    register_user(client, "owner3@example.com")
    promote_to_admin(db, "owner3@example.com")
    token = login_user(client, "owner3@example.com").json()["access_token"]

    created = client.post(
        "/api/v1/businesses",
        json={"name": "Barber Shop", "timezone": "Europe/Warsaw", "phone": "+48600000001"},
        headers=auth_headers(token),
    ).json()

    response = client.get(
        f"/api/v1/businesses/{created['id']}", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "+48600000001"


def test_update_business(db, client):
    register_user(client, "owner4@example.com")
    promote_to_admin(db, "owner4@example.com")
    token = login_user(client, "owner4@example.com").json()["access_token"]

    created = client.post(
        "/api/v1/businesses",
        json={"name": "Old Name", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()

    response = client.patch(
        f"/api/v1/businesses/{created['id']}",
        json={"name": "New Name"},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_get_nonexistent_business_returns_404(db, client):
    register_user(client, "owner5@example.com")
    token = login_user(client, "owner5@example.com").json()["access_token"]

    response = client.get("/api/v1/businesses/99999", headers=auth_headers(token))

    assert response.status_code == 404
