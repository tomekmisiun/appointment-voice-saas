from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies.rate_limit import rate_limit
from app.db.session import get_db
from app.schemas.health import HealthStatus, ReadinessHealth
from app.services.health_service import check_database, check_redis, check_s3, get_readiness


router = APIRouter(prefix="/health", tags=["health"])


def readiness_response(health: ReadinessHealth):
    if health.status == "ok":
        return health

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=health.model_dump(exclude_none=True),
    )


@router.get(
    "",
    response_model=HealthStatus,
    summary="Basic health check",
    description="Backward-compatible process health endpoint.",
)
def health_check():
    return HealthStatus(status="ok")


@router.get(
    "/live",
    response_model=HealthStatus,
    summary="Liveness probe",
)
def liveness_check():
    return HealthStatus(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessHealth,
    response_model_exclude_none=True,
    summary="Readiness probe",
    description="Checks database, Redis, and optional object storage dependencies required to serve traffic.",
)
def readiness_check(db: Session = Depends(get_db)):
    return readiness_response(get_readiness(db))


@router.get(
    "/db",
    response_model=ReadinessHealth,
    response_model_exclude_none=True,
    summary="Database health check",
)
def db_health_check(db: Session = Depends(get_db)):
    database_check = check_database(db)
    return readiness_response(
        ReadinessHealth(
            status=database_check.status,
            checks={"database": database_check},
        )
    )


@router.get(
    "/redis",
    response_model=ReadinessHealth,
    response_model_exclude_none=True,
    summary="Redis health check",
)
def redis_health():
    redis_check = check_redis()
    return readiness_response(
        ReadinessHealth(
            status=redis_check.status,
            checks={"redis": redis_check},
        )
    )


@router.get(
    "/s3",
    response_model=ReadinessHealth,
    response_model_exclude_none=True,
    summary="Object storage health check",
)
def s3_health():
    s3_check = check_s3()
    return readiness_response(
        ReadinessHealth(
            status=s3_check.status,
            checks={"object_storage": s3_check},
        )
    )


@router.get(
    "/limited",
    dependencies=[Depends(rate_limit())],
    summary="Rate-limited example endpoint",
    description="Demonstrates Redis-backed IP rate limiting for template projects.",
)
def limited_endpoint():
    return {"message": "ok"}
