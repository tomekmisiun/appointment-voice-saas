# API Rules

REST-style FastAPI API with versioned routes under `/api/v1`.

## Endpoints

- Route handlers MUST stay thin: validate input, call services, map responses.
- Routers MUST stay separated by domain.
- Use correct HTTP methods, status codes, and response models.
- Raise `HTTPException` only in route handlers and dependencies.
- Services MUST NOT raise `HTTPException`.
- MUST NOT expose internal stack traces or implementation details to clients.

## Authentication And Authorization

- Non-public routes MUST use `get_current_user`, `require_permission`, or another
  explicit auth dependency.
- Public routes (health, metrics, signed webhooks) MUST be intentional and
  documented in code or docs.
- MUST NOT add new routes to `app/api/legacy.py` unless the user explicitly
  requested legacy compatibility.
- New endpoints MUST live under the versioned API surface (`/api/v1`).

## Validation

- Use Pydantic schemas for request and response validation.
- Validate query parameters with FastAPI tools such as `Query`.
- Keep request and response schemas in `app/schemas`.

## Changes

- Every new endpoint MUST have tests before commit.
- API behavior changes MUST update `README.md` and any affected file under
  `docs/` when one exists.
