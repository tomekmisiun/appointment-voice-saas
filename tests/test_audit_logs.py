import pytest

from app.core.ids import uuid7
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def make_admin(db, user_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    user.role = "admin"
    db.commit()


@pytest.fixture
def admin_user(db, client):
    token, user_id = create_user_and_login(
        db,
        client,
        f"audit-admin-{uuid7().hex}@example.com",
    )

    make_admin(db, user_id)

    return {
        "id": user_id,
        "headers": auth_headers(token),
    }


@pytest.fixture
def regular_user(db, client):
    token, user_id = create_user_and_login(
        db,
        client,
        f"audit-user-{uuid7().hex}@example.com",
    )

    return {
        "id": user_id,
        "headers": auth_headers(token),
    }


def get_latest_audit_log(db) -> AuditLog:
    return db.query(AuditLog).order_by(AuditLog.id.desc()).first()


def test_cleanup_old_audit_logs_deletes_rows_past_retention(db, monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.models.audit_log import AuditLog
    from app.services.audit_log_service import cleanup_old_audit_logs

    monkeypatch.setattr(
        "app.services.audit_log_service.settings.audit_log_retention_days",
        30,
    )

    old_log = AuditLog(
        tenant_id=1,
        admin_id=None,
        action=AuditAction.USER_UPDATED.value,
        target_user_id=2,
        created_at=datetime.now(timezone.utc) - timedelta(days=45),
    )
    recent_log = AuditLog(
        tenant_id=1,
        admin_id=None,
        action=AuditAction.USER_UPDATED.value,
        target_user_id=2,
    )
    db.add_all([old_log, recent_log])
    db.commit()
    initial_count = db.query(AuditLog).count()

    deleted_count = cleanup_old_audit_logs(db)

    assert deleted_count == 1
    assert db.query(AuditLog).count() == initial_count - 1


def test_admin_update_user_creates_audit_log(
    db,
    client,
    admin_user,
    regular_user,
):
    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"email": "audit-updated@example.com"},
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    audit_log = get_latest_audit_log(db)

    assert audit_log.admin_id == admin_user["id"]
    assert audit_log.action == AuditAction.USER_UPDATED
    assert audit_log.target_user_id == regular_user["id"]


def test_admin_update_user_rolls_back_when_audit_write_fails(
    db,
    client,
    admin_user,
    regular_user,
    monkeypatch,
):
    original_user = (
        db.query(User)
        .filter(User.id == regular_user["id"])
        .first()
    )
    original_email = original_user.email

    def failing_create_audit_log(*args, **kwargs):
        if kwargs.get("commit") is False:
            raise RuntimeError("audit write failed")

        from app.services.audit_log_service import create_audit_log

        return create_audit_log(*args, **kwargs)

    monkeypatch.setattr(
        "app.api.routes.users.create_audit_log",
        failing_create_audit_log,
    )

    with pytest.raises(RuntimeError, match="audit write failed"):
        client.patch(
            f"/users/{regular_user['id']}",
            json={"email": "audit-should-not-persist@example.com"},
            headers=admin_user["headers"],
        )

    db.rollback()
    db.expire_all()
    user = db.query(User).filter(User.id == regular_user["id"]).first()

    assert user.email == original_email


def test_self_update_does_not_create_audit_log(db, client, regular_user):
    audit_log_count = db.query(AuditLog).count()

    response = client.patch(
        f"/users/{regular_user['id']}",
        json={"email": "audit-self-updated@example.com"},
        headers=regular_user["headers"],
    )

    assert response.status_code == 200
    assert db.query(AuditLog).count() == audit_log_count


def test_admin_deactivate_user_creates_audit_log(
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

    audit_log = get_latest_audit_log(db)

    assert audit_log.admin_id == admin_user["id"]
    assert audit_log.action == AuditAction.USER_DEACTIVATED
    assert audit_log.target_user_id == regular_user["id"]


def test_admin_activate_user_creates_audit_log(
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

    audit_log = get_latest_audit_log(db)

    assert audit_log.admin_id == admin_user["id"]
    assert audit_log.action == AuditAction.USER_ACTIVATED
    assert audit_log.target_user_id == regular_user["id"]


def test_admin_delete_user_creates_audit_log(
    db,
    client,
    admin_user,
):
    _, target_user_id = create_user_and_login(
        db,
        client,
        "audit-delete@example.com",
    )

    response = client.delete(
        f"/users/{target_user_id}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 204

    audit_log = get_latest_audit_log(db)

    assert audit_log.admin_id == admin_user["id"]
    assert audit_log.action == AuditAction.USER_DELETED
    assert audit_log.target_user_id == target_user_id


def test_list_audit_logs_requires_auth(client):
    response = client.get("/admin/audit-logs")

    assert response.status_code == 401


def test_list_audit_logs_forbidden_for_regular_user(client, regular_user):
    response = client.get(
        "/admin/audit-logs",
        headers=regular_user["headers"],
    )

    assert response.status_code == 403


def test_admin_can_list_audit_logs(db, client, admin_user, regular_user):
    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )

    response = client.get(
        "/admin/audit-logs",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1
    assert data[0]["admin_id"] == admin_user["id"]
    assert data[0]["action"] == AuditAction.USER_DEACTIVATED
    assert data[0]["target_user_id"] == regular_user["id"]
    assert "created_at" in data[0]


def test_admin_can_filter_audit_logs_by_action(
    db,
    client,
    admin_user,
    regular_user,
):
    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )
    client.patch(
        f"/users/{regular_user['id']}/activate",
        headers=admin_user["headers"],
    )

    response = client.get(
        f"/admin/audit-logs?action={AuditAction.USER_ACTIVATED}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1
    assert all(item["action"] == AuditAction.USER_ACTIVATED for item in data)


def test_admin_can_filter_audit_logs_by_admin_id(
    db,
    client,
    admin_user,
    regular_user,
):
    other_admin_token, other_admin_id = create_user_and_login(
        db,
        client,
        f"audit-other-admin-{uuid7().hex}@example.com",
    )
    make_admin(db, other_admin_id)

    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )
    client.patch(
        f"/users/{regular_user['id']}/activate",
        headers=auth_headers(other_admin_token),
    )

    response = client.get(
        f"/admin/audit-logs?admin_id={other_admin_id}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1
    assert all(item["admin_id"] == other_admin_id for item in data)


def test_admin_can_filter_audit_logs_by_target_user_id(
    db,
    client,
    admin_user,
    regular_user,
):
    _, other_target_user_id = create_user_and_login(
        db,
        client,
        f"audit-other-target-{uuid7().hex}@example.com",
    )

    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )
    client.patch(
        f"/users/{other_target_user_id}/deactivate",
        headers=admin_user["headers"],
    )

    response = client.get(
        f"/admin/audit-logs?target_user_id={other_target_user_id}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 1
    assert all(item["target_user_id"] == other_target_user_id for item in data)


def test_invalid_audit_log_action_filter_returns_422(client, admin_user):
    response = client.get(
        "/admin/audit-logs?action=invalid.action",
        headers=admin_user["headers"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_audit_logs_are_ordered_newest_first(
    db,
    client,
    admin_user,
    regular_user,
):
    client.patch(
        f"/users/{regular_user['id']}/deactivate",
        headers=admin_user["headers"],
    )
    client.patch(
        f"/users/{regular_user['id']}/activate",
        headers=admin_user["headers"],
    )

    response = client.get(
        f"/admin/audit-logs?target_user_id={regular_user['id']}",
        headers=admin_user["headers"],
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) >= 2
    assert data[0]["id"] > data[1]["id"]
    assert data[0]["action"] == AuditAction.USER_ACTIVATED
    assert data[1]["action"] == AuditAction.USER_DEACTIVATED
