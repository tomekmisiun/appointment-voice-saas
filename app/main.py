from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.domain_errors import DomainError
from app.core.exception_handlers import (
    domain_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.error_tracking import initialize_error_tracking
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.api.legacy import legacy_api_router
from app.api.openapi import configure_openapi
from app.api.routes.health import router as health_router
from app.api.routes.metrics import router as metrics_router
from app.api.v1 import api_v1_router
from app.core.config import settings
from app.core.metrics import configure_metrics
from app.core.runtime import configure_runtime_middleware
from app.core.shutdown import wait_for_in_flight_requests
from app.db.pool_config import log_db_pool_configuration

configure_logging()
configure_metrics()
initialize_error_tracking()


@asynccontextmanager
async def lifespan(application: FastAPI):
    del application
    log_db_pool_configuration()
    yield
    await wait_for_in_flight_requests(settings.api_shutdown_grace_seconds)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    summary="Reusable FastAPI backend template",
    lifespan=lifespan,
)
configure_openapi(app)

app.add_middleware(RequestContextMiddleware)
configure_runtime_middleware(app, settings)
app.add_exception_handler(DomainError, domain_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


def include_application_routers(application: FastAPI) -> None:
    application.include_router(health_router)
    application.include_router(metrics_router)
    application.include_router(api_v1_router)
    if settings.legacy_routes_enabled:
        application.include_router(legacy_api_router)


include_application_routers(app)
