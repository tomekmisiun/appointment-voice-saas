"""Per-worker resource isolation for pytest-xdist.

Must be imported and applied before any ``app.*`` modules are imported,
since settings (database URL, Redis DB index) are read once at import time.
"""

import os


def configure_worker_isolation() -> None:
    """Point this xdist worker at its own Postgres database and Redis DB.

    Each worker gets a dedicated database (``<base>_gw0``, ``<base>_gw1``,
    ...) so workers never share schema state, and a dedicated Redis logical
    database so rate-limit/queue keys never collide between workers.

    No-op when not running under xdist (``PYTEST_XDIST_WORKER`` unset), so
    serial test runs keep using the shared database configured via
    ``TEST_DATABASE_URL``/``REDIS_DB``.
    """
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")

    if not worker_id:
        return

    worker_index = int(worker_id.removeprefix("gw"))

    test_database_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://app_user:app_password@test_db:5432/app_test_db",
    )
    os.environ["TEST_DATABASE_URL"] = f"{test_database_url}_{worker_id}"

    # Reserve Redis DB 0 for serial (non-xdist) runs; workers start at 1.
    base_redis_db = int(os.environ.get("REDIS_DB", "0"))
    os.environ["REDIS_DB"] = str(base_redis_db + worker_index + 1)
