from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text

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
