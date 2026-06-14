"""Tests for Staff CRUD (AVS-B002)."""

from tests.database import auth_headers, login_user, promote_to_admin, register_user


def _setup_admin_with_business(db, client, email: str, business_name: str = "Test Salon") -> tuple[str, int]:
    register_user(client, email)
    promote_to_admin(db, email)
    token = login_user(client, email).json()["access_token"]
    biz = client.post(
        "/api/v1/businesses",
        json={"name": business_name, "timezone": "Europe/Warsaw"},
        headers=auth_headers(token),
    ).json()
    return token, biz["id"]


def test_admin_can_create_staff(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "s1@example.com")

    response = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Marek"},
        headers=auth_headers(token),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Marek"
    assert data["is_active"] is True
    assert data["business_id"] == biz_id


def test_list_staff(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "s2@example.com")
    client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Anna", "phone": "+48600000002"},
        headers=auth_headers(token),
    )

    response = client.get(
        f"/api/v1/businesses/{biz_id}/staff", headers=auth_headers(token)
    )

    assert response.status_code == 200
    assert any(s["name"] == "Anna" for s in response.json())


def test_deactivate_staff(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "s3@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Piotr"},
        headers=auth_headers(token),
    ).json()

    response = client.patch(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_inactive_staff_excluded_by_default(db, client):
    token, biz_id = _setup_admin_with_business(db, client, "s4@example.com")
    staff = client.post(
        f"/api/v1/businesses/{biz_id}/staff",
        json={"name": "Inactive"},
        headers=auth_headers(token),
    ).json()
    client.patch(
        f"/api/v1/businesses/{biz_id}/staff/{staff['id']}",
        json={"is_active": False},
        headers=auth_headers(token),
    )

    response = client.get(
        f"/api/v1/businesses/{biz_id}/staff", headers=auth_headers(token)
    )

    assert not any(s["id"] == staff["id"] for s in response.json())
