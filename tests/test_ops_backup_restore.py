from sqlalchemy import text

from app.models.tenant import Tenant
from app.models.user import User
from tests.database import engine


def test_logical_backup_restore_rehearsal_preserves_user_row(db):
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    user = User(
        email="backup-rehearsal@example.com",
        hashed_password="hashed-password",
        role="user",
        is_active=True,
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TEMP TABLE backup_ops_users ON COMMIT DROP AS "
                "SELECT * FROM users WHERE id = :user_id"
            ),
            {"user_id": user.id},
        )
        connection.execute(
            text("DELETE FROM users WHERE id = :user_id"),
            {"user_id": user.id},
        )
        deleted_row = connection.execute(
            text("SELECT email FROM users WHERE id = :user_id"),
            {"user_id": user.id},
        ).fetchone()

        assert deleted_row is None

        connection.execute(
            text("INSERT INTO users SELECT * FROM backup_ops_users")
        )
        restored_row = connection.execute(
            text("SELECT email FROM users WHERE id = :user_id"),
            {"user_id": user.id},
        ).fetchone()

    assert restored_row is not None
    assert restored_row[0] == "backup-rehearsal@example.com"
