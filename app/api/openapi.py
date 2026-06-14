from fastapi import FastAPI, status

from app.core.config import settings
from app.schemas.errors import ErrorResponse


OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Registration, login, token refresh/logout, and password reset flows."
        ),
    },
    {
        "name": "users",
        "description": "User listing, profile reads, and self/admin updates.",
    },
    {
        "name": "admin",
        "description": "Admin-only operations and audit log inspection.",
    },
    {
        "name": "files",
        "description": "Authenticated file uploads backed by object storage.",
    },
    {
        "name": "health",
        "description": "Process and dependency health checks for orchestration.",
    },
    {
        "name": "metrics",
        "description": "Prometheus-compatible application metrics.",
    },
    {
        "name": "webhooks",
        "description": "Signed inbound webhook processing with replay protection.",
    },
]

ERROR_RESPONSES = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "Bad request.",
    },
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Authentication required or credentials are invalid.",
    },
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Authenticated but not authorized for this action.",
    },
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Requested resource was not found.",
    },
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Request conflicts with current resource state.",
    },
    status.HTTP_422_UNPROCESSABLE_ENTITY: {
        "model": ErrorResponse,
        "description": "Request validation failed.",
    },
    status.HTTP_429_TOO_MANY_REQUESTS: {
        "model": ErrorResponse,
        "description": "Rate limit exceeded.",
    },
}

AUTH_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: ERROR_RESPONSES[status.HTTP_401_UNAUTHORIZED],
    status.HTTP_422_UNPROCESSABLE_ENTITY: ERROR_RESPONSES[
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ],
}

PROTECTED_ERROR_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: ERROR_RESPONSES[status.HTTP_401_UNAUTHORIZED],
    status.HTTP_403_FORBIDDEN: ERROR_RESPONSES[status.HTTP_403_FORBIDDEN],
    status.HTTP_404_NOT_FOUND: ERROR_RESPONSES[status.HTTP_404_NOT_FOUND],
    status.HTTP_422_UNPROCESSABLE_ENTITY: ERROR_RESPONSES[
        status.HTTP_422_UNPROCESSABLE_ENTITY
    ],
}

ADMIN_ERROR_RESPONSES = {
    **PROTECTED_ERROR_RESPONSES,
}

RATE_LIMITED_ERROR_RESPONSES = {
    **AUTH_ERROR_RESPONSES,
    status.HTTP_429_TOO_MANY_REQUESTS: ERROR_RESPONSES[
        status.HTTP_429_TOO_MANY_REQUESTS
    ],
}


def configure_openapi(app: FastAPI) -> None:
    app.openapi_tags = OPENAPI_TAGS

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = FastAPI.openapi(app)
        schema["info"]["description"] = (
            f"{settings.app_name} — multi-tenant booking and availability "
            "backend built on a production FastAPI foundation (JWT auth, admin "
            "workflows, audit logs, Redis rate limiting, object storage). "
            "Salon domain: businesses, staff, services, hours, availability slots, "
            "bookings with DB-level double-booking protection. IVR/SMS/calendar: planned."
        )
        schema["components"]["securitySchemes"]["HTTPBearer"] = {
            **schema["components"]["securitySchemes"].get("HTTPBearer", {}),
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Use the access token returned by login or refresh. "
                "Send it as `Authorization: Bearer <access_token>`."
            ),
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
