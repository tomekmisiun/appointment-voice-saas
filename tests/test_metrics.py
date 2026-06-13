def test_metrics_endpoint_exposes_prometheus_text(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP http_requests_total" in response.text
    assert "# TYPE http_request_duration_seconds histogram" in response.text
    assert 'app_info{environment="' in response.text
    assert 'service="fastapi-production-foundation"' in response.text


def test_metrics_record_requests(client):
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200
    assert 'http_requests_total{method="GET",path="/health",status_code="200"}' in (
        response.text
    )
    assert 'http_request_duration_seconds_count{method="GET",path="/health",' in (
        response.text
    )


def test_metrics_use_route_templates_instead_of_raw_paths(client):
    client.get("/users/123")

    response = client.get("/metrics")

    assert 'path="/users/{user_id}"' in response.text
    assert 'path="/users/123"' not in response.text


def test_metrics_endpoint_does_not_record_itself(client):
    client.get("/metrics")
    response = client.get("/metrics")

    assert 'path="/metrics"' not in response.text


def test_metrics_requires_bearer_token_when_auth_enabled(monkeypatch, client):
    monkeypatch.setattr("app.core.config.settings.metrics_require_auth", True)
    monkeypatch.setattr(
        "app.core.config.settings.metrics_bearer_token",
        "metrics-test-token",
    )

    unauthorized = client.get("/metrics")
    assert unauthorized.status_code == 401

    authorized = client.get(
        "/metrics",
        headers={"Authorization": "Bearer metrics-test-token"},
    )
    assert authorized.status_code == 200


def test_metrics_record_dependency_checks(client):
    client.get("/health/ready")

    response = client.get("/metrics")

    assert 'dependency_checks_total{dependency="database",status="ok"}' in response.text
    assert 'dependency_checks_total{dependency="redis",status="ok"}' in response.text
    assert 'dependency_health_status{dependency="database"} 1.0' in response.text
    assert 'dependency_health_status{dependency="redis"} 1.0' in response.text
