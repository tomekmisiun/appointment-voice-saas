from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.user import User

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
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_config, "head")


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
