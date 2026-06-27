"""
Central read-only guard for public demo sessions.

Blocks POST/PUT/PATCH/DELETE for any request whose access JWT carries
``is_public_demo=True``.  The allow-list below covers the only mutations
a demo session legitimately needs (auth bootstrap, logout, token refresh).

``require_non_demo_user`` on individual routes remains as defense-in-depth:
a future route that accidentally omits it is still blocked here.

Not-blocked by design:
- Requests with no Authorization header (webhooks, workers, health checks)
- Requests with an invalid or expired JWT (rejected later by auth dependency)
- Normal authenticated users (JWT lacks ``is_public_demo`` claim)
- Safe HTTP methods (GET, HEAD, OPTIONS)
"""

import json
import logging

from jose import JWTError
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.security import decode_token


logger = logging.getLogger("app.demo_guard")

_MUTATION_METHODS = frozenset(["POST", "PUT", "PATCH", "DELETE"])

# Mutations a demo session must be able to make.
# Each entry must have an explicit reason; no business-data mutations allowed.
_DEMO_ALLOWLIST: frozenset[str] = frozenset([
    "/api/v1/auth/demo",     # demo session creation itself
    "/api/v1/auth/logout",   # user must be able to end the demo session
    "/api/v1/auth/refresh",  # short-lived access token renewal
])

_DEMO_403_BODY = json.dumps(
    {"detail": "This action is disabled in public demo mode."}
).encode()
_DEMO_403_HEADERS = [
    (b"content-type", b"application/json"),
    (b"content-length", str(len(_DEMO_403_BODY)).encode()),
]


class DemoReadOnlyMiddleware:
    """ASGI middleware: deny-by-default for demo session mutations."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        if method not in _MUTATION_METHODS:
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in _DEMO_ALLOWLIST:
            await self.app(scope, receive, send)
            return

        if _is_public_demo_token(scope):
            logger.warning(
                "demo_read_only_blocked",
                extra={"method": method, "path": path},
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": _DEMO_403_HEADERS,
                }
            )
            await send(
                {"type": "http.response.body", "body": _DEMO_403_BODY, "more_body": False}
            )
            return

        await self.app(scope, receive, send)


def _is_public_demo_token(scope: Scope) -> bool:
    """Return True if the request carries a valid JWT with is_public_demo=True."""
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    auth_value: str | None = None
    for name, value in headers:
        if name.lower() == b"authorization":
            auth_value = value.decode("latin-1")
            break

    if not auth_value or not auth_value.startswith("Bearer "):
        return False

    token = auth_value[len("Bearer "):]
    try:
        payload = decode_token(token)
        return payload.get("is_public_demo") is True
    except (JWTError, Exception):
        return False
