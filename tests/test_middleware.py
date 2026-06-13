from uuid import UUID


def test_request_id_header_is_added(client):
    response = client.get("/health")

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 7


def test_request_id_header_is_preserved(client):
    request_id = "test-request-id"

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_process_time_header_is_added(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert float(response.headers["X-Process-Time"]) >= 0


def test_request_id_is_set_as_sentry_tag(client, monkeypatch):
    tags = []
    request_id = "test-request-id"

    def fake_set_tag(key, value):
        tags.append((key, value))

    monkeypatch.setattr("app.core.middleware.sentry_sdk.set_tag", fake_set_tag)

    response = client.get(
        "/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert ("request_id", request_id) in tags
