"""Tests for Service CRUD (AVS-B003)."""

from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _setup(db, client, email: str) -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": "Salon", "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def test_admin_can_create_service(db, client):
    token, biz_id = _setup(db, client, "svc1@example.com")

    response = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={"name": "Haircut", "duration_minutes": 30},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Haircut"
    assert data["duration_minutes"] == 30
    assert data["is_active"] is True


def test_service_requires_valid_duration(db, client):
    token, biz_id = _setup(db, client, "svc2@example.com")

    response = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={"name": "Bad", "duration_minutes": 0},
        headers=auth_headers(token),
    )

    assert response.status_code == 422


def test_list_services_excludes_inactive(db, client):
    token, biz_id = _setup(db, client, "svc3@example.com")
    svc = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={"name": "Gone", "duration_minutes": 15},
        headers=auth_headers(token),
    ).json()
    client.patch(
        f"/api/v1/businesses/{biz_id}/services/{svc['id']}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    response = client.get(
        f"/api/v1/businesses/{biz_id}/services", headers=auth_headers(token)
    )

    assert not any(s["id"] == svc["id"] for s in response.json())


def test_service_with_price_metadata(db, client):
    token, biz_id = _setup(db, client, "svc4@example.com")

    response = client.post(
        f"/api/v1/businesses/{biz_id}/services",
        json={
            "name": "Premium Cut",
            "duration_minutes": 60,
            "price_minor_units": 5000,
            "currency": "PLN",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["price_minor_units"] == 5000
    assert data["currency"] == "PLN"
