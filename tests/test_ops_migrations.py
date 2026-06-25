from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.config import settings
from tests.database import engine, reset_test_database, run_test_migrations


def build_alembic_config() -> Config:
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", settings.test_database_url)

    return alembic_config


def test_migrations_have_single_head():
    script = ScriptDirectory.from_config(build_alembic_config())
    heads = script.get_heads()

    assert len(heads) == 1


def test_migration_downgrade_and_upgrade_round_trip():
    alembic_config = build_alembic_config()
    script = ScriptDirectory.from_config(alembic_config)
    head_revision = script.get_revision(script.get_current_head())

    reset_test_database()
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, head_revision.down_revision)

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    assert current_revision == head_revision.down_revision

    command.upgrade(alembic_config, "head")

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    assert current_revision == script.get_current_head()


def test_reset_and_migrate_produces_core_tables():
    reset_test_database()
    run_test_migrations()

    with engine.connect() as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public'"
                )
            )
        }

    assert {
        "users",
        "tenants",
        "audit_logs",
        "uploaded_files",
        "idempotency_records",
        "webhook_events",
        "alembic_version",
    }.issubset(table_names)


def test_sac003_business_memberships_migration_upgrade_and_downgrade():
    revision = "sac003a2b3c4d5e6"
    alembic_config = build_alembic_config()
    script = ScriptDirectory.from_config(alembic_config)
    down_revision = script.get_revision(revision).down_revision

    reset_test_database()
    command.upgrade(alembic_config, "head")

    inspector = inspect(engine)
    assert "business_memberships" in inspector.get_table_names()

    index_names = {index["name"] for index in inspector.get_indexes("business_memberships")}
    assert {
        "uix_business_memberships_business_user",
        "uix_business_memberships_business_staff_active",
        "ix_business_memberships_tenant_business_status",
        "ix_business_memberships_user_id",
        "ix_business_memberships_staff_id",
    }.issubset(index_names)

    constraint_names = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("business_memberships")
    }
    assert {
        "ck_business_memberships_staff_role_requires_staff_id",
        "ck_business_memberships_role_valid",
        "ck_business_memberships_status_valid",
    }.issubset(constraint_names)

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("business_memberships")}
    assert {
        "fk_business_memberships_business_same_tenant",
        "fk_business_memberships_user_same_tenant",
        "fk_business_memberships_staff_same_business",
        "fk_business_memberships_invited_by_same_tenant",
        "fk_business_memberships_revoked_by_same_tenant",
    }.issubset(fk_names)

    command.downgrade(alembic_config, down_revision)

    inspector = inspect(engine)
    assert "business_memberships" not in inspector.get_table_names()
    assert "uix_businesses_tenant_id_id" not in {
        index["name"] for index in inspector.get_indexes("businesses")
    }

    command.upgrade(alembic_config, "head")

    inspector = inspect(engine)
    assert "business_memberships" in inspector.get_table_names()
