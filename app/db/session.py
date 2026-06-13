from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def build_engine(database_url: str | None = None):
    effective_database_url = database_url or settings.database_url
    connect_args = {}

    if settings.db_statement_timeout_ms > 0:
        connect_args["options"] = (
            f"-c statement_timeout={settings.db_statement_timeout_ms}"
        )

    return create_engine(
        effective_database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=settings.db_pool_pre_ping,
        pool_timeout=settings.db_pool_timeout_seconds,
        connect_args=connect_args,
    )


engine = build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
