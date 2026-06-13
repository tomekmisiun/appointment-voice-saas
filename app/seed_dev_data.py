from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User
from app.services.tenant_seed_service import ensure_default_tenant


DEV_PASSWORD = "devpassword123"


@dataclass(frozen=True)
class DevUserSeed:
    email: str
    role: str


DEV_USERS = (
    DevUserSeed(email="admin@example.local", role="platform_admin"),
    DevUserSeed(email="user@example.local", role="user"),
)


def seed_dev_users(db, *, commit: bool = True) -> dict[str, str]:
    tenant = ensure_default_tenant(db, commit=False)

    results: dict[str, str] = {}

    for dev_user in DEV_USERS:
        existing_user = (
            db.query(User)
            .filter(
                User.tenant_id == tenant.id,
                User.email == dev_user.email,
            )
            .first()
        )

        if existing_user is None:
            db.add(
                User(
                    tenant_id=tenant.id,
                    email=dev_user.email,
                    hashed_password=hash_password(DEV_PASSWORD),
                    role=dev_user.role,
                    is_active=True,
                )
            )
            results[dev_user.email] = "created"
            continue

        results[dev_user.email] = "skipped"

    if commit:
        db.commit()
    else:
        db.flush()

    return results


def main() -> None:
    configure_logging()

    if settings.environment != "development":
        raise SystemExit(
            "seed_dev_data only runs when ENVIRONMENT=development",
        )

    db = SessionLocal()

    try:
        results = seed_dev_users(db)
    finally:
        db.close()

    for email, status in results.items():
        print(f"{email}: {status}")


if __name__ == "__main__":
    main()
