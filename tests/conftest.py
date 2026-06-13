import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from tests.database import (  # noqa: E402
    TestingSessionLocal,
    reset_test_database,
    run_test_migrations,
)
from app.services.tenant_seed_service import ensure_default_tenant  # noqa: E402


reset_test_database()
run_test_migrations()

_seed_session = TestingSessionLocal()
try:
    ensure_default_tenant(_seed_session)
finally:
    _seed_session.close()


@pytest.fixture()
def db():
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clean_rate_limit_keys():
    from app.core.redis import redis_client

    keys = list(redis_client.scan_iter("rate_limit:*"))

    if keys:
        redis_client.delete(*keys)

    yield

    keys = list(redis_client.scan_iter("rate_limit:*"))

    if keys:
        redis_client.delete(*keys)
