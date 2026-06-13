from app.db.session import get_db
from app.main import app


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_liveness_check(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_check(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "database": {"status": "ok"},
            "redis": {"status": "ok"},
        },
    }


def test_database_health_check(client):
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "database": {"status": "ok"},
        },
    }


def test_redis_health_check(client):
    response = client.get("/health/redis")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "redis": {"status": "ok"},
        },
    }


def test_readiness_check_returns_503_when_database_is_unavailable(client):
    class UnavailableDatabase:
        def execute(self, statement):
            raise RuntimeError("database connection failed")

    def override_get_db():
        yield UnavailableDatabase()

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["checks"]["database"] == {
        "status": "unavailable",
        "message": "database unavailable",
    }
    assert response.json()["checks"]["redis"] == {"status": "ok"}


def test_database_health_check_returns_503_when_database_is_unavailable(client):
    class UnavailableDatabase:
        def execute(self, statement):
            raise RuntimeError("database connection failed")

    def override_get_db():
        yield UnavailableDatabase()

    app.dependency_overrides[get_db] = override_get_db

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {
            "database": {
                "status": "unavailable",
                "message": "database unavailable",
            },
        },
    }


def test_readiness_check_returns_503_when_redis_is_unavailable(client, monkeypatch):
    class UnavailableRedis:
        def ping(self):
            raise RuntimeError("redis connection failed")

    monkeypatch.setattr(
        "app.services.health_service.redis_client",
        UnavailableRedis(),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["checks"]["database"] == {"status": "ok"}
    assert response.json()["checks"]["redis"] == {
        "status": "unavailable",
        "message": "redis unavailable",
    }


def test_s3_health_check(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.readiness_check_s3_enabled", True)

    class OkProvider:
        def verify_bucket_access(self):
            return None

    class OkStorageService:
        provider = OkProvider()

    monkeypatch.setattr(
        "app.services.health_service.get_storage_service",
        lambda: OkStorageService(),
    )

    response = client.get("/health/s3")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "object_storage": {"status": "ok"},
        },
    }


def test_readiness_check_returns_503_when_s3_is_unavailable(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.readiness_check_s3_enabled", True)
    class FailingProvider:
        def verify_bucket_access(self):
            raise RuntimeError("s3 unavailable")

    class FailingStorageService:
        provider = FailingProvider()

    monkeypatch.setattr(
        "app.services.health_service.get_storage_service",
        lambda: FailingStorageService(),
    )

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["object_storage"] == {
        "status": "unavailable",
        "message": "object storage unavailable",
    }


def test_readiness_check_skips_s3_when_disabled(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.readiness_check_s3_enabled", False)

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert "object_storage" not in response.json()["checks"]


def test_readiness_check_includes_s3_when_enabled(client, monkeypatch):
    monkeypatch.setattr("app.core.config.settings.readiness_check_s3_enabled", True)

    class OkProvider:
        def verify_bucket_access(self):
            return None

    class OkStorageService:
        provider = OkProvider()

    monkeypatch.setattr(
        "app.services.health_service.get_storage_service",
        lambda: OkStorageService(),
    )

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"]["object_storage"] == {"status": "ok"}


def test_redis_health_check_returns_503_when_redis_is_unavailable(
    client,
    monkeypatch,
):
    class UnavailableRedis:
        def ping(self):
            raise RuntimeError("redis connection failed")

    monkeypatch.setattr(
        "app.services.health_service.redis_client",
        UnavailableRedis(),
    )

    response = client.get("/health/redis")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unavailable",
        "checks": {
            "redis": {
                "status": "unavailable",
                "message": "redis unavailable",
            },
        },
    }
