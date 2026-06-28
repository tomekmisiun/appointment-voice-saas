import os
import re
from urllib.parse import urlsplit, urlunsplit

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User

_SAFE_DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+$")


def _create_database_if_missing(database_url: str) -> None:
    """Create the target Postgres database if it does not exist yet.

    Used so each pytest-xdist worker can have its own test database
    (e.g. ``app_test_db_gw0``) without requiring manual provisioning.
    """
    parts = urlsplit(database_url)
    db_name = parts.path.lstrip("/")

    if not _SAFE_DATABASE_NAME.match(db_name):
        raise ValueError(f"Unsafe test database name: {db_name!r}")

    admin_url = urlunsplit(parts._replace(path="/postgres"))
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            ).first()

            if exists is None:
                connection.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin_engine.dispose()


# Only pytest-xdist workers use a per-worker database name (app_test_db_gwN)
# that needs provisioning on the fly. Serial runs use the pre-provisioned
# TEST_DATABASE_URL as-is, so they don't need (or want) a maintenance-DB
# connection.
if os.environ.get("PYTEST_XDIST_WORKER"):
    _create_database_if_missing(settings.test_database_url)

engine = create_engine(settings.test_database_url)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def reset_test_database() -> None:
    with engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))


def run_test_migrations() -> None:
    # env.py skips DATABASE_URL override when ENVIRONMENT=test, ensuring
    # migrations target the test DB even in a development Docker environment.
    _orig = os.environ.get("ENVIRONMENT")
    os.environ["ENVIRONMENT"] = "test"
    try:
        alembic_config = Config("alembic.ini")
        alembic_config.set_main_option("sqlalchemy.url", settings.test_database_url)
        command.upgrade(alembic_config, "head")
    finally:
        if _orig is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = _orig


def register_user(client, email: str, password: str = "password123", tenant_slug: str | None = None):
    headers = {}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
        headers=headers,
    )


def login_user(client, email: str, password: str = "password123", tenant_slug: str | None = None):
    headers = {}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )


def auth_headers(access_token: str, tenant_slug: str | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {access_token}"}
    if tenant_slug is not None:
        headers["X-Tenant-Slug"] = tenant_slug
    return headers


def promote_to_admin(db, email: str) -> User:
    user = db.query(User).filter(User.email == email).one()
    user.role = "admin"
    db.commit()
    db.refresh(user)
    return user
