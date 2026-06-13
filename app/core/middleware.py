import logging
import time

import sentry_sdk
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.ids import uuid7
from app.core.metrics import get_route_path, observe_request
from app.core.request_context import request_id_var
from app.core.shutdown import decrement_in_flight_requests, increment_in_flight_requests
from app.core.tenant_context import clear_tenant_context


logger = logging.getLogger("app.requests")


def _get_header(headers: list[tuple[bytes, bytes]], name: str) -> str | None:
    header_name = name.lower().encode("latin-1")

    for key, value in headers:
        if key.lower() == header_name:
            return value.decode("latin-1")

    return None


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        headers = scope.get("headers", [])
        request_id = _get_header(headers, "X-Request-ID") or str(uuid7())
        scope.setdefault("state", {})["request_id"] = request_id
        request_id_token = request_id_var.set(request_id)
        sentry_sdk.set_tag("request_id", request_id)
        clear_tenant_context()
        increment_in_flight_requests()

        method = scope.get("method", "GET")
        path = scope.get("path", "")
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.perf_counter() - start_time
                response_headers = list(message.get("headers", []))
                response_headers.append(
                    (b"x-request-id", request_id.encode("latin-1"))
                )
                response_headers.append(
                    (b"x-process-time", str(process_time).encode("latin-1"))
                )
                message = {**message, "headers": response_headers}

            await send(message)

        try:
            logger.info(
                "request_started",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                },
            )

            await self.app(scope, receive, send_wrapper)

            process_time = time.perf_counter() - start_time

            if path != "/metrics":
                observe_request(
                    method=method,
                    path=get_route_path(scope),
                    status_code=status_code,
                    duration_seconds=process_time,
                )

            logger.info(
                "request_finished",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "process_time": process_time,
                },
            )
        finally:
            decrement_in_flight_requests()
            request_id_var.reset(request_id_token)
