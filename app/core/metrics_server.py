import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app.core.config import settings
from app.core.metrics import render_metrics


class MetricsRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/metrics":
            self.send_error(404)
            return

        if not self._is_authorized():
            self.send_error(401)
            return

        body = render_metrics().encode("utf-8")
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "text/plain; version=0.0.4; charset=utf-8",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _is_authorized(self) -> bool:
        if not settings.metrics_require_auth:
            return True

        expected_token = settings.metrics_bearer_token.strip()

        if expected_token == "":
            return False

        authorization = self.headers.get("Authorization")

        if authorization is None or not authorization.startswith("Bearer "):
            return False

        provided_token = authorization.removeprefix("Bearer ").strip()
        return provided_token == expected_token

    def log_message(self, format: str, *args) -> None:
        return


_metrics_server: ThreadingHTTPServer | None = None
_metrics_server_thread: threading.Thread | None = None


def start_metrics_server(*, host: str, port: int) -> int:
    global _metrics_server, _metrics_server_thread

    if _metrics_server is not None:
        return _metrics_server.server_address[1]

    _metrics_server = ThreadingHTTPServer((host, port), MetricsRequestHandler)
    bound_port = _metrics_server.server_address[1]
    _metrics_server_thread = threading.Thread(
        target=_metrics_server.serve_forever,
        name="worker-metrics-server",
        daemon=True,
    )
    _metrics_server_thread.start()
    return bound_port


def stop_metrics_server() -> None:
    global _metrics_server, _metrics_server_thread

    if _metrics_server is None:
        return

    _metrics_server.shutdown()
    _metrics_server.server_close()
    _metrics_server = None
    _metrics_server_thread = None
