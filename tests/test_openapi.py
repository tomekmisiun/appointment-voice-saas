from app.api.v1 import API_V1_PREFIX


def get_openapi_schema(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    return response.json()


def test_openapi_includes_api_description_and_security_scheme(client):
    schema = get_openapi_schema(client)

    assert "Production-oriented FastAPI backend template" in schema["info"]["description"]
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"


def test_openapi_tags_include_descriptions(client):
    schema = get_openapi_schema(client)
    tags_by_name = {tag["name"]: tag for tag in schema["tags"]}

    assert "auth" in tags_by_name
    assert "users" in tags_by_name
    assert "description" in tags_by_name["auth"]


def test_openapi_documents_error_response_schema(client):
    schema = get_openapi_schema(client)
    error_schema = schema["components"]["schemas"]["ErrorResponse"]

    assert "error" in error_schema["properties"]
    assert "examples" in error_schema


def test_openapi_documents_versioned_route_summaries(client):
    schema = get_openapi_schema(client)
    login_operation = schema["paths"][f"{API_V1_PREFIX}/auth/login"]["post"]

    assert login_operation["summary"] == "Login and receive JWT tokens"
    assert "401" in login_operation["responses"]
    assert "422" in login_operation["responses"]


def test_openapi_documents_bearer_auth_on_protected_route(client):
    schema = get_openapi_schema(client)
    me_operation = schema["paths"][f"{API_V1_PREFIX}/auth/me"]["get"]

    assert "security" in me_operation
    assert {"HTTPBearer": []} in me_operation["security"]
