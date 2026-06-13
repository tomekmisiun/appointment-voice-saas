from starlette.requests import Request

from app.core.client_ip import get_client_ip


def build_request(
    *,
    client_host: str = "10.0.0.1",
    headers: dict[str, str] | None = None,
) -> Request:
    header_lines = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": header_lines,
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
        "http_version": "1.1",
    }

    return Request(scope)


def test_get_client_ip_uses_direct_client_by_default(monkeypatch):
    monkeypatch.setattr(
        "app.core.client_ip.settings.rate_limit_trust_forwarded_headers",
        False,
    )

    request = build_request(client_host="203.0.113.10")

    assert get_client_ip(request) == "203.0.113.10"


def test_get_client_ip_uses_forwarded_for_when_trusted(monkeypatch):
    monkeypatch.setattr(
        "app.core.client_ip.settings.rate_limit_trust_forwarded_headers",
        True,
    )

    request = build_request(
        client_host="10.0.0.1",
        headers={"X-Forwarded-For": "198.51.100.20, 10.0.0.1"},
    )

    assert get_client_ip(request) == "198.51.100.20"


def test_get_client_ip_uses_real_ip_when_forwarded_for_missing(monkeypatch):
    monkeypatch.setattr(
        "app.core.client_ip.settings.rate_limit_trust_forwarded_headers",
        True,
    )

    request = build_request(
        client_host="10.0.0.1",
        headers={"X-Real-IP": "198.51.100.30"},
    )

    assert get_client_ip(request) == "198.51.100.30"
