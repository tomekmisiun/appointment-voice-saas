from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.metrics import observe_dependency_check
from app.core.redis import redis_client
from app.schemas.health import DependencyHealth, ReadinessHealth
from app.services.storage_service import get_storage_service


def check_database(db: Session) -> DependencyHealth:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        observe_dependency_check(dependency="database", status="unavailable")
        return DependencyHealth(
            status="unavailable",
            message="database unavailable",
        )

    observe_dependency_check(dependency="database", status="ok")
    return DependencyHealth(status="ok")


def check_redis() -> DependencyHealth:
    try:
        redis_client.ping()
    except Exception:
        observe_dependency_check(dependency="redis", status="unavailable")
        return DependencyHealth(
            status="unavailable",
            message="redis unavailable",
        )

    observe_dependency_check(dependency="redis", status="ok")
    return DependencyHealth(status="ok")


def check_s3() -> DependencyHealth:
    if not settings.readiness_check_s3_enabled:
        return DependencyHealth(
            status="ok",
            message="object storage check disabled",
        )

    try:
        get_storage_service().provider.verify_bucket_access()
    except Exception:
        observe_dependency_check(dependency="object_storage", status="unavailable")
        return DependencyHealth(
            status="unavailable",
            message="object storage unavailable",
        )

    observe_dependency_check(dependency="object_storage", status="ok")
    return DependencyHealth(status="ok")


def get_readiness(db: Session) -> ReadinessHealth:
    checks = {
        "database": check_database(db),
        "redis": check_redis(),
    }

    if settings.readiness_check_s3_enabled:
        checks["object_storage"] = check_s3()

    if any(check.status != "ok" for check in checks.values()):
        return ReadinessHealth(status="unavailable", checks=checks)

    return ReadinessHealth(status="ok", checks=checks)
