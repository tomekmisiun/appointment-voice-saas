from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.tenant_seed_service import ensure_default_tenant


def main() -> None:
    configure_logging()

    db = SessionLocal()

    try:
        tenant = ensure_default_tenant(db)
    finally:
        db.close()

    print(f"default tenant ready: slug={tenant.slug} id={tenant.id}")


if __name__ == "__main__":
    main()
