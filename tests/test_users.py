import pytest
from time import sleep

from app.core.cache import delete_cache_pattern, get_json_cache, set_json_cache
from app.core.ids import uuid7
from app.core.security import hash_password
from app.models.user import User


def create_user_in_db(db, email: str, *, tenant_id: int = 1) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        tenant_id=tenant_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_and_login(db, client, email: str) -> tuple[str, int]:
    payload = {
        "email": email,
        "password": "password123",
    }

    client.post("/auth/register", json=payload)

    user = db.query(User).filter(User.email == email).first()

    response = client.post("/auth/login", json=payload)
    token = response.json()["access_token"]

    return token, user.id


@pytest.fixture
def regular_user(db, client):
    token, user_id = create_user_and_login(
        db,
        client,
        f"regular-user-{uuid7().hex}@example.com",
    )

    return {
        "token": token,
        "id": user_id,
        "headers": auth_headers(token),
    }


@pytest.fixture
def admin_user(db, client):
    email = f"admin-user-{uuid7().hex}@example.com"

    token, user_id = create_user_and_login(
        db,
        client,
        email,
    )

    make_admin(db, email)

    return {
        "token": token,
        "id": user_id,
        "headers": auth_headers(token),
    }


def make_admin(db, email: str) -> None:
    user = db.query(User).filter(User.email == email).first()
    user.role = "admin"
    db.commit()


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def users_page_items(response) -> list:
    return response.json()["items"]


def users_page_payload(response) -> dict:
    return response.json()


def test_list_users_requires_auth(client):
    response = client.get("/users/")

    assert response.status_code == 401


def test_list_users_forbidden_for_regular_user(client, regular_user):
    response = client.get(
        "/users/",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_admin_can_list_users(client, admin_user):
    response = client.get(
        "/users/",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    assert len(users_page_items(response)) >= 1


def test_user_can_get_himself(client, regular_user):
    response = client.get(
        f"/users/{regular_user['id']}",
        headers=regular_user["headers"],
    )

    assert response.status_code == 200


def test_user_cannot_get_other_user(db, client, regular_user):
    _, other_user_id = create_user_and_login(
        db,
        client,
        "other@example.com",
    )

    response = client.get(
        f"/users/{other_user_id}",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_admin_can_get_any_user(db, client, admin_user):
    _, normal_user_id = create_user_and_login(
        db,
        client,
        "normal@example.com",
    )

    response = client.get(
        f"/users/{normal_user_id}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200


def test_user_can_update_himself(client, regular_user):
    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"email": "updated@example.com"},
        headers=regular_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["email"] == "updated@example.com"


def test_user_cannot_update_self_is_active(client, regular_user):
    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"is_active": False},
        headers=regular_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_admin_can_update_user_is_active(client, admin_user, regular_user):
    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"is_active": False},
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_admin_invalid_role_update_returns_422(client, admin_user, regular_user):
    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"role": "banana"},
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_user_cannot_update_other_user(db, client, regular_user):
    _, other_user_id = create_user_and_login(
        db,
        client,
        "userb@example.com",
    )

    response = client.patch(
        f"/users/{other_user_id}",
        json={"email": "hacked@example.com"},
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_admin_can_update_any_user(db, client, admin_user):
    _, user_id = create_user_and_login(
        db,
        client,
        "victim@example.com",
    )

    response = client.patch(
        f"/users/{user_id}",
        json={"email": "updated-admin@example.com"},
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    assert response.json()["email"] == "updated-admin@example.com"


def test_admin_can_delete_user(db, client, admin_user):
    _, user_id = create_user_and_login(
        db,
        client,
        "victim-delete@example.com",
    )

    response = client.delete(
        f"/users/{user_id}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 204


def test_user_cannot_delete_other_user(db, client, regular_user):
    _, other_user_id = create_user_and_login(
        db,
        client,
        "victim-delete-user@example.com",
    )

    response = client.delete(
        f"/users/{other_user_id}",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_admin_can_list_users_with_pagination(db, client, admin_user):
    for i in range(15):
        create_user_in_db(db, f"pagination-user-{i}@example.com")

    response = client.get(
        "/users/?page=1&size=5",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    assert len(users_page_items(response)) == 5


def test_admin_can_list_users_with_keyset_cursor(db, client, admin_user):
    prefix = f"keyset-user-{uuid7().hex}"
    for i in range(12):
        create_user_in_db(db, f"{prefix}-{i:02d}@example.com")

    first_response = client.get(
        f"/users/?size=5&search={prefix}&search_mode=prefix",
        headers=admin_user["headers"],
    )
    second_response = client.get(
        f"/users/?size=5&cursor={first_response.json()['next_cursor']}"
        f"&search={prefix}&search_mode=prefix",
        headers=admin_user["headers"],
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(users_page_items(first_response)) == 5
    assert first_response.json()["next_cursor"] is not None
    assert len(users_page_items(second_response)) == 5

    first_ids = {user["id"] for user in users_page_items(first_response)}
    second_ids = {user["id"] for user in users_page_items(second_response)}
    assert first_ids.isdisjoint(second_ids)


def test_admin_can_search_users_with_contains_mode(db, client, admin_user):
    marker = f"contains-{uuid7().hex}"
    matching_email = f"alpha-{marker}-beta@example.com"
    non_matching_email = f"gamma-{uuid7().hex}@example.com"
    create_user_in_db(db, matching_email)
    create_user_in_db(db, non_matching_email)

    response = client.get(
        f"/users/?search={marker}&search_mode=contains&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    emails = {user["email"] for user in users_page_items(response)}
    assert matching_email in emails
    assert non_matching_email not in emails


def test_admin_prefix_search_does_not_match_middle_substring(db, client, admin_user):
    marker = f"prefix-{uuid7().hex}"
    email = f"start-{marker}-end@example.com"
    create_user_in_db(db, email)

    prefix_response = client.get(
        f"/users/?search={marker}&search_mode=prefix&size=100",
        headers=admin_user["headers"],
    )
    contains_response = client.get(
        f"/users/?search={marker}&search_mode=contains&size=100",
        headers=admin_user["headers"],
    )

    assert prefix_response.status_code == 200
    assert contains_response.status_code == 200
    assert users_page_items(prefix_response) == []
    assert {user["email"] for user in users_page_items(contains_response)} == {email}


def test_list_users_rejects_cursor_with_legacy_page(client, admin_user):
    response = client.get(
        "/users/?page=2&cursor=invalid&size=5",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_list_users_rejects_invalid_cursor(client, admin_user):
    response = client.get(
        "/users/?cursor=not-a-valid-cursor&size=5",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_admin_can_list_second_page(db, client, admin_user):
    for i in range(15):
        create_user_in_db(db, f"pagination-page2-user-{i}@example.com")

    response = client.get(
        "/users/?page=2&size=5",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200
    assert len(users_page_items(response)) == 5


def test_pagination_page_must_be_positive(client, admin_user):
    response = client.get(
        "/users/?page=0&size=10",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_pagination_size_must_be_positive(client, admin_user):
    response = client.get(
        "/users/?page=1&size=0",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_pagination_size_must_not_exceed_limit(client, admin_user):
    response = client.get(
        "/users/?page=1&size=101",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_admin_can_sort_users_by_email_desc(db, client, admin_user):
    create_user_and_login(db, client, "c-user@example.com")
    create_user_and_login(db, client, "a-user@example.com")
    create_user_and_login(db, client, "b-user@example.com")

    response = client.get(
        "/users/?sort_by=email&sort_order=desc&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    emails = [user["email"] for user in users_page_items(response)]

    filtered_emails = [
        email
        for email in emails
        if email in {
            "a-user@example.com",
            "b-user@example.com",
            "c-user@example.com",
        }
    ]

    assert filtered_emails == [
        "c-user@example.com",
        "b-user@example.com",
        "a-user@example.com",
    ]


def test_invalid_sort_order_returns_422(client, admin_user):
    response = client.get(
        "/users/?sort_by=email&sort_order=banana&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_invalid_sort_by_returns_422(client, admin_user):
    response = client.get(
        "/users/?sort_by=banana&sort_order=asc&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_admin_can_filter_users_by_role(db, client, admin_user):
    create_user_and_login(
        db,
        client,
        "normal-user@example.com",
    )

    create_user_and_login(
        db,
        client,
        "admin-filter@example.com",
    )

    make_admin(db, "admin-filter@example.com")

    response = client.get(
        "/users/?role=admin&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    roles = [user["role"] for user in users_page_items(response)]

    assert all(role == "admin" for role in roles)


def test_admin_can_filter_users_by_is_active(
    db,
    client,
    admin_user,
):
    create_user_and_login(
        db,
        client,
        "active-user@example.com",
    )

    create_user_and_login(
        db,
        client,
        "inactive-user@example.com",
    )

    inactive_user = (
        db.query(User)
        .filter(User.email == "inactive-user@example.com")
        .first()
    )

    inactive_user.is_active = False
    db.commit()

    response = client.get(
        "/users/?is_active=false&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    users = users_page_items(response)

    assert len(users) > 0
    assert all(user["is_active"] is False for user in users)


def test_invalid_role_filter_returns_422(client, admin_user):
    response = client.get(
        "/users/?role=banana",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422


def test_admin_can_search_users_by_email(db, client, admin_user):
    client.post(
        "/auth/register",
        json={
            "email": "tomek@example.com",
            "password": "password123",
        },
    )

    client.post(
        "/auth/register",
        json={
            "email": "admin@gmail.com",
            "password": "password123",
        },
    )

    response = client.get(
        "/users?search=tomek",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = users_page_items(response)

    assert len(data) == 1
    assert data[0]["email"] == "tomek@example.com"


def test_admin_list_users_uses_cached_result_for_same_query(
    db,
    client,
    admin_user,
):
    email_prefix = f"cache-hit-{uuid7().hex}"
    original_email = f"{email_prefix}@example.com"
    updated_email = f"{email_prefix}-updated@example.com"

    create_user_and_login(db, client, original_email)

    first_response = client.get(
        f"/users/?search={email_prefix}&page=1&size=100",
        headers=admin_user["headers"],
    )
    user = db.query(User).filter(User.email == original_email).one()
    user.email = updated_email
    db.commit()
    second_response = client.get(
        f"/users/?search={email_prefix}&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_response.json()["items"][0]["email"] == original_email


def test_admin_list_users_cache_is_invalidated_after_user_update(
    db,
    client,
    admin_user,
):
    email_prefix = f"cache-invalidate-{uuid7().hex}"
    original_email = f"{email_prefix}@example.com"
    updated_email = f"{email_prefix}-updated@example.com"

    _, user_id = create_user_and_login(db, client, original_email)

    first_response = client.get(
        f"/users/?search={email_prefix}&page=1&size=100",
        headers=admin_user["headers"],
    )
    update_response = client.patch(
        f"/users/{user_id}",
        json={"email": updated_email},
        headers=admin_user["headers"],
    )
    old_search_response = client.get(
        f"/users/?search={original_email}&page=1&size=100",
        headers=admin_user["headers"],
    )
    new_search_response = client.get(
        f"/users/?search={updated_email}&page=1&size=100",
        headers=admin_user["headers"],
    )

    assert first_response.status_code == 200
    assert update_response.status_code == 200
    assert old_search_response.status_code == 200
    assert new_search_response.status_code == 200
    assert users_page_items(old_search_response) == []
    assert users_page_items(new_search_response)[0]["email"] == updated_email


def test_json_cache_expires_values():
    cache_key = f"test-cache-expiry:{uuid7().hex}"

    set_json_cache(cache_key, {"cached": True}, ttl_seconds=1)

    assert get_json_cache(cache_key) == {"cached": True}

    sleep(1.1)

    assert get_json_cache(cache_key) is None
    delete_cache_pattern(cache_key)


def test_admin_can_deactivate_user(
    db,
    client,
    admin_user,
    regular_user,
):
    response = client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_active"] is False


def test_admin_can_activate_user(
    db,
    client,
    admin_user,
    regular_user,
):
    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )

    response = client.patch(
        f"/users/{regular_user['id']}/activate",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_active"] is True


def test_deactivate_nonexistent_user_returns_404(
    client,
    admin_user,
):
    response = client.patch(
        "/users/99999/deactivate",
        headers=admin_user["headers"],
    )

    assert response.status_code == 404


def test_activate_nonexistent_user_returns_404(
    client,
    admin_user,
):
    response = client.patch(
        "/users/99999/activate",
        headers=admin_user["headers"],
    )

    assert response.status_code == 404


def test_regular_user_cannot_deactivate_user(
    client,
    regular_user,
):
    response = client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_regular_user_cannot_activate_user(
    client,
    regular_user,
):
    response = client.patch(
        f"/users/{regular_user['id']}/activate",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_list_users_returns_only_active_users_by_default(
    client,
    admin_user,
    regular_user,
):
    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )

    response = client.get(
        "/users",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    users = users_page_items(response)

    user_ids = [user["id"] for user in users]

    assert regular_user["id"] not in user_ids
