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
    # Redis ships with 16 logical DBs (0-15) by default, so this caps the
    # usable worker count at 15.
    base_redis_db = int(os.environ.get("REDIS_DB", "0"))
    worker_redis_db = base_redis_db + worker_index + 1

    if worker_redis_db > 15:
        raise RuntimeError(
            f"pytest-xdist worker {worker_id!r} would use Redis DB "
            f"{worker_redis_db}, which exceeds Redis's default 16 logical "
            "DBs (0-15). Reduce the worker count."
        )

    os.environ["REDIS_DB"] = str(worker_redis_db)
