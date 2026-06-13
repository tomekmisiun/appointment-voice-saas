from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.password_reset_service import cleanup_expired_password_reset_tokens


def main() -> None:
    configure_logging()
    db = SessionLocal()

    try:
        cleanup_expired_password_reset_tokens(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
