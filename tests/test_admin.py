from app.models.user import User


def test_admin_requires_auth(client):
    response = client.get("/admin")

    assert response.status_code == 401


def test_admin_forbidden_for_regular_user(client):
    user_data = {
        "email": "user@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=user_data)

    login_response = client.post("/auth/login", json=user_data)
    token = login_response.json()["access_token"]

    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_access(db, client):
    user_data = {
        "email": "admin@example.com",
        "password": "password123",
    }

    client.post("/auth/register", json=user_data)

    user = db.query(User).filter(
        User.email == "admin@example.com"
    ).first()

    user.role = "admin"
    db.commit()

    login_response = client.post(
        "/auth/login",
        json=user_data,
    )

    token = login_response.json()["access_token"]

    response = client.get(
        "/admin",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200