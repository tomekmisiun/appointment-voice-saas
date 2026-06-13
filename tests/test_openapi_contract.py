from app.api.v1 import API_V1_PREFIX
from tests.test_api_versioning import V1_ROUTE_CHECKS
from tests.test_openapi import get_openapi_schema


BEARER_PROTECTED_V1_OPERATIONS = [
    ("get", f"{API_V1_PREFIX}/auth/me"),
    ("get", f"{API_V1_PREFIX}/users/"),
    ("get", f"{API_V1_PREFIX}/admin"),
    ("get", f"{API_V1_PREFIX}/admin/audit-logs"),
    ("get", f"{API_V1_PREFIX}/admin/tenants"),
    ("post", f"{API_V1_PREFIX}/admin/tenants"),
    ("post", f"{API_V1_PREFIX}/files/upload"),
]

PUBLIC_V1_OPERATIONS = [
    ("post", f"{API_V1_PREFIX}/auth/register"),
    ("post", f"{API_V1_PREFIX}/auth/login"),
    ("post", f"{API_V1_PREFIX}/auth/refresh"),
    ("post", f"{API_V1_PREFIX}/auth/password-reset/request"),
    ("post", f"{API_V1_PREFIX}/auth/password-reset/confirm"),
]


def test_openapi_documents_all_v1_smoke_routes(client):
    schema = get_openapi_schema(client)
    paths = schema["paths"]

    for method, path, _expected_status in V1_ROUTE_CHECKS:
        assert path in paths, f"missing OpenAPI path: {path}"
        assert method.lower() in paths[path], f"missing OpenAPI method: {method} {path}"


def test_openapi_v1_protected_routes_declare_bearer_security(client):
    schema = get_openapi_schema(client)
    paths = schema["paths"]

    for method, path in BEARER_PROTECTED_V1_OPERATIONS:
        operation = paths[path][method]

        assert {"HTTPBearer": []} in operation["security"]


def test_openapi_v1_webhook_route_documents_signature_based_auth(client):
    schema = get_openapi_schema(client)
    operation = schema["paths"][f"{API_V1_PREFIX}/webhooks/inbound"]["post"]

    assert "HMAC" in operation["description"]
    assert "security" not in operation


def test_openapi_v1_public_routes_document_auth_error_responses(client):
    schema = get_openapi_schema(client)
    paths = schema["paths"]

    for method, path in PUBLIC_V1_OPERATIONS:
        operation = paths[path][method]
        responses = operation["responses"]

        assert "422" in responses
        assert (
            responses["422"]["content"]["application/json"]["schema"]["$ref"]
            == "#/components/schemas/ErrorResponse"
        )


def test_openapi_v1_protected_routes_document_error_response_schema(client):
    schema = get_openapi_schema(client)
    paths = schema["paths"]

    for method, path in BEARER_PROTECTED_V1_OPERATIONS:
        operation = paths[path][method]
        unauthorized = operation["responses"]["401"]["content"]["application/json"][
            "schema"
        ]

        assert unauthorized["$ref"] == "#/components/schemas/ErrorResponse"


def test_openapi_documents_health_and_metrics_paths(client):
    schema = get_openapi_schema(client)
    paths = schema["paths"]

    assert "/health" in paths
    assert "/health/ready" in paths
    assert "/metrics" in paths
