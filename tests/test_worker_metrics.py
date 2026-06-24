import time

import httpx

from app.core.metrics import (
    configure_metrics,
    observe_calendar_provider_request,
    observe_integration_reconciliation_requeued,
    observe_sms_provider_request,
    observe_worker_failed_queue_depth,
    observe_worker_job,
)
from app.core.metrics_server import start_metrics_server, stop_metrics_server


def _get_metrics(url: str, **kwargs) -> httpx.Response:
    last_error = None

    for _ in range(20):
        try:
            return httpx.get(url, timeout=2.0, **kwargs)
        except httpx.ConnectError as exc:
            last_error = exc
            time.sleep(0.05)

    raise last_error


def test_worker_metrics_server_exposes_prometheus_text(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", False)
    configure_metrics()
    observe_worker_job(job_type="demo", status="completed")
    port = start_metrics_server(host="127.0.0.1", port=0)

    try:
        response = _get_metrics(f"http://127.0.0.1:{port}/metrics")

        assert response.status_code == 200
        assert "worker_jobs_total" in response.text
    finally:
        stop_metrics_server()


def test_worker_failed_queue_depth_gauge_is_exposed(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", False)
    configure_metrics()
    observe_worker_failed_queue_depth(7)
    port = start_metrics_server(host="127.0.0.1", port=0)

    try:
        response = _get_metrics(f"http://127.0.0.1:{port}/metrics")

        assert response.status_code == 200
        assert "worker_failed_queue_depth 7.0" in response.text
    finally:
        stop_metrics_server()


def test_provider_failure_metrics_are_exposed(monkeypatch):
    # Counters are process-global and never reset between tests, so use a
    # label value unique to this test instead of asserting an absolute count
    # (other tests legitimately increment provider="null"/"twilio" too).
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", False)
    configure_metrics()
    observe_sms_provider_request(provider="__test_sms_provider__", status="failure")
    observe_calendar_provider_request(
        provider="__test_calendar_provider__", operation="sync", status="failure"
    )
    port = start_metrics_server(host="127.0.0.1", port=0)

    try:
        response = _get_metrics(f"http://127.0.0.1:{port}/metrics")

        assert response.status_code == 200
        assert (
            'sms_provider_requests_total{provider="__test_sms_provider__",status="failure"} 1.0'
            in response.text
        )
        assert (
            'calendar_provider_requests_total{operation="sync",'
            'provider="__test_calendar_provider__",status="failure"} 1.0'
            in response.text
        )
    finally:
        stop_metrics_server()


def test_integration_reconciliation_requeued_metric_is_exposed(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", False)
    configure_metrics()
    observe_integration_reconciliation_requeued(
        record_type="__test_record_type__", count=3
    )
    port = start_metrics_server(host="127.0.0.1", port=0)

    try:
        response = _get_metrics(f"http://127.0.0.1:{port}/metrics")

        assert response.status_code == 200
        assert (
            'integration_reconciliation_requeued_total{record_type="__test_record_type__"} 3.0'
            in response.text
        )
    finally:
        stop_metrics_server()


def test_worker_metrics_server_requires_bearer_token(monkeypatch):
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", True)
    monkeypatch.setattr(
        "app.core.config.settings.metrics_bearer_token",
        "metrics-test-token",
    )
    configure_metrics()
    port = start_metrics_server(host="127.0.0.1", port=0)

    try:
        unauthorized = _get_metrics(f"http://127.0.0.1:{port}/metrics")
        authorized = _get_metrics(
            f"http://127.0.0.1:{port}/metrics",
            headers={"Authorization": "Bearer metrics-test-token"},
        )

        assert unauthorized.status_code == 401
        assert authorized.status_code == 200
    finally:
        stop_metrics_server()
