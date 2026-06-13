import pytest

from app.core.security import verify_password
from app.models.tenant import Tenant
from app.models.user import User
from app.seed_dev_data import DEV_PASSWORD, DEV_USERS, seed_dev_users


def test_seed_dev_users_creates_expected_accounts(db, monkeypatch):
    monkeypatch.setattr("app.seed_dev_data.settings.environment", "development")

    results = seed_dev_users(db, commit=False)

    assert results == {
        "admin@example.local": "created",
        "user@example.local": "created",
    }

    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()

    for dev_user in DEV_USERS:
        user = (
            db.query(User)
            .filter(
                User.tenant_id == tenant.id,
                User.email == dev_user.email,
            )
            .one()
        )

        assert user.role == dev_user.role
        assert user.is_active is True
        assert verify_password(DEV_PASSWORD, user.hashed_password)


def test_seed_dev_users_is_idempotent(db, monkeypatch):
    monkeypatch.setattr("app.seed_dev_data.settings.environment", "development")

    first_results = seed_dev_users(db, commit=False)
    second_results = seed_dev_users(db, commit=False)

    assert first_results == {
        "admin@example.local": "created",
        "user@example.local": "created",
    }
    assert second_results == {
        "admin@example.local": "skipped",
        "user@example.local": "skipped",
    }


def test_seed_dev_data_refuses_non_development_environments(monkeypatch):
    monkeypatch.setattr("app.seed_dev_data.settings.environment", "production")

    with pytest.raises(SystemExit, match="ENVIRONMENT=development"):
        from app.seed_dev_data import main

        main()
