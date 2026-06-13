from unittest.mock import MagicMock

import pytest

from app.core.domain_errors import BadRequestError, NotFoundError
from app.core.exception_handlers import domain_error_handler
from app.main import app


@pytest.mark.anyio
async def test_domain_error_handler_returns_standard_error_envelope():
    request = MagicMock()
    request.method = "GET"
    request.url.path = "/tenants/1"

    response = await domain_error_handler(
        request=request,
        exc=NotFoundError("Tenant not found"),
    )

    assert response.status_code == 404
    assert response.body == (
        b'{"error":{"code":"not_found","message":"Tenant not found"}}'
    )


def test_domain_error_handler_is_registered(client):
    original_overrides = app.dependency_overrides.copy()

    def failing_dependency():
        raise BadRequestError("Service layer validation failed")

    from app.api.dependencies.auth import get_current_user

    app.dependency_overrides[get_current_user] = failing_dependency

    try:
        response = client.get("/users/1")
    finally:
        app.dependency_overrides = original_overrides

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "bad_request",
            "message": "Service layer validation failed",
        }
    }
