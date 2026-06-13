import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.domain_errors import DomainError


ERROR_CODES_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_413_CONTENT_TOO_LARGE: "payload_too_large",
    422: "validation_error",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limit_exceeded",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details=None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    content = {
        "error": {
            "code": code,
            "message": message,
        }
    }

    if details is not None:
        content["error"]["details"] = details

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers,
    )


def get_error_code(status_code: int) -> str:
    return ERROR_CODES_BY_STATUS.get(status_code, "api_error")


async def domain_error_handler(
    request: Request,
    exc: DomainError,
) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=get_error_code(exc.status_code),
        message=exc.message,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "API error"

    return error_response(
        status_code=exc.status_code,
        code=get_error_code(exc.status_code),
        message=detail,
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        status_code=422,
        code="validation_error",
        message="Request validation failed",
        details=exc.errors(),
    )


logger = logging.getLogger("app.errors")


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.exception(
        "unhandled_exception",
        extra={"method": request.method, "path": request.url.path},
    )

    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message="An unexpected error occurred",
    )
