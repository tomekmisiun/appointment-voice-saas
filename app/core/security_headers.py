from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        hsts_enabled: bool = False,
        hsts_max_age_seconds: int = 31536000,
    ) -> None:
        super().__init__(app)
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age_seconds = hsts_max_age_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )

        if self.hsts_enabled:
            response.headers.setdefault(
                "Strict-Transport-Security",
                f"max-age={self.hsts_max_age_seconds}; includeSubDomains",
            )

        return response
