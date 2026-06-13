from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from tests.database import engine


def test_test_database_is_at_alembic_head():
    alembic_config = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_config)
    expected_head = script.get_current_head()

    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_revision = context.get_current_revision()

    assert current_revision == expected_head
