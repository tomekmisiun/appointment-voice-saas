import os
from typing import TYPE_CHECKING

from prometheus_client import (
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

from app.core.config import settings


REQUEST_DURATION_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
)

_registry: CollectorRegistry | None = None
_multiproc_dir: str | None = None
_metrics_configured = False
_http_requests_total: Counter | None = None
_http_request_duration_seconds: Histogram | None = None
_worker_jobs_total: Counter | None = None
_worker_maintenance_runs_total: Counter | None = None
_dependency_checks_total: Counter | None = None
_dependency_health_status: Gauge | None = None
_worker_failed_queue_depth: Gauge | None = None
_sms_provider_requests_total: Counter | None = None
_calendar_provider_requests_total: Counter | None = None
_app_info: Gauge | None = None

if TYPE_CHECKING:
    from app.core.config import Settings


def configure_metrics(app_settings: "Settings | None" = None) -> None:
    global _registry, _multiproc_dir, _metrics_configured
    global _http_requests_total, _http_request_duration_seconds
    global _worker_jobs_total, _worker_maintenance_runs_total
    global _dependency_checks_total, _dependency_health_status, _app_info
    global _worker_failed_queue_depth
    global _sms_provider_requests_total, _calendar_provider_requests_total

    if _metrics_configured:
        return

    active_settings = app_settings or settings
    configured_multiproc_dir = active_settings.prometheus_multiproc_dir.strip()

    if not configured_multiproc_dir:
        os.environ.pop("PROMETHEUS_MULTIPROC_DIR", None)

    if configured_multiproc_dir:
        os.makedirs(configured_multiproc_dir, exist_ok=True)
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = configured_multiproc_dir
        _multiproc_dir = configured_multiproc_dir
        _registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(_registry)
    else:
        _multiproc_dir = None
        _registry = None

    counter_kwargs = {"multiprocess_mode": "livesum"} if _multiproc_dir else {}
    gauge_kwargs = {"multiprocess_mode": "mostrecent"} if _multiproc_dir else {}

    _http_requests_total = Counter(
        "http_requests_total",
        "Total HTTP requests.",
        ["method", "path", "status_code"],
        **counter_kwargs,
    )
    _http_request_duration_seconds = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds.",
        ["method", "path", "status_code"],
        buckets=REQUEST_DURATION_BUCKETS,
        **counter_kwargs,
    )
    _worker_jobs_total = Counter(
        "worker_jobs_total",
        "Total worker jobs processed.",
        ["job_type", "status"],
        **counter_kwargs,
    )
    _worker_maintenance_runs_total = Counter(
        "worker_maintenance_runs_total",
        "Total worker maintenance runs.",
        ["status"],
        **counter_kwargs,
    )
    _dependency_checks_total = Counter(
        "dependency_checks_total",
        "Total dependency health checks.",
        ["dependency", "status"],
        **counter_kwargs,
    )
    _dependency_health_status = Gauge(
        "dependency_health_status",
        "Latest dependency health status (1=ok, 0=unavailable).",
        ["dependency"],
        **gauge_kwargs,
    )
    _worker_failed_queue_depth = Gauge(
        "worker_failed_queue_depth",
        "Number of jobs currently sitting in the worker dead-letter queue.",
        **gauge_kwargs,
    )
    _sms_provider_requests_total = Counter(
        "sms_provider_requests_total",
        "Total SMS send attempts per provider.",
        ["provider", "status"],
        **counter_kwargs,
    )
    _calendar_provider_requests_total = Counter(
        "calendar_provider_requests_total",
        "Total calendar provider requests.",
        ["provider", "operation", "status"],
        **counter_kwargs,
    )

    app_info_labels = ["service", "environment"]
    app_info_label_values = {
        "service": "fastapi-production-foundation",
        "environment": active_settings.environment,
    }

    if active_settings.metrics_instance_id.strip():
        app_info_labels.append("instance_id")
        app_info_label_values["instance_id"] = active_settings.metrics_instance_id.strip()

    _app_info = Gauge(
        "app_info",
        "Application info.",
        app_info_labels,
        **gauge_kwargs,
    )
    _app_info.labels(**app_info_label_values).set(1)
    _metrics_configured = True


def get_route_path(scope: dict) -> str:
    route = scope.get("route")

    if route is None:
        return scope.get("path", "unknown")

    return getattr(route, "path", scope.get("path", "unknown"))


def observe_request(
    *,
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    if _http_requests_total is None or _http_request_duration_seconds is None:
        configure_metrics()

    labels = {
        "method": method,
        "path": path,
        "status_code": str(status_code),
    }
    _http_requests_total.labels(**labels).inc()
    _http_request_duration_seconds.labels(**labels).observe(duration_seconds)


def observe_worker_job(*, job_type: str, status: str) -> None:
    if _worker_jobs_total is None:
        configure_metrics()

    _worker_jobs_total.labels(job_type=job_type, status=status).inc()


def observe_worker_maintenance(*, status: str) -> None:
    if _worker_maintenance_runs_total is None:
        configure_metrics()

    _worker_maintenance_runs_total.labels(status=status).inc()


def observe_worker_failed_queue_depth(depth: int) -> None:
    if _worker_failed_queue_depth is None:
        configure_metrics()

    _worker_failed_queue_depth.set(depth)


def observe_sms_provider_request(*, provider: str, status: str) -> None:
    if _sms_provider_requests_total is None:
        configure_metrics()

    _sms_provider_requests_total.labels(provider=provider, status=status).inc()


def observe_calendar_provider_request(*, provider: str, operation: str, status: str) -> None:
    if _calendar_provider_requests_total is None:
        configure_metrics()

    _calendar_provider_requests_total.labels(
        provider=provider, operation=operation, status=status
    ).inc()


def observe_dependency_check(*, dependency: str, status: str) -> None:
    if _dependency_checks_total is None or _dependency_health_status is None:
        configure_metrics()

    _dependency_checks_total.labels(dependency=dependency, status=status).inc()
    _dependency_health_status.labels(dependency=dependency).set(
        1 if status == "ok" else 0
    )


def render_metrics() -> str:
    if _http_requests_total is None:
        configure_metrics()

    if _registry is not None:
        return generate_latest(_registry).decode("utf-8")

    return generate_latest(REGISTRY).decode("utf-8")


def mark_metrics_process_dead() -> None:
    if _multiproc_dir is None:
        return

    multiprocess.mark_process_dead(os.getpid())
