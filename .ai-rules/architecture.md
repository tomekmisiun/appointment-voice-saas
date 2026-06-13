# Architecture Rules

FastAPI backend using SQLAlchemy, Alembic, PostgreSQL, and Redis.
Preserve the current architecture unless an explicit task requires changing it.

## Layers

- `app/api/routes` and `app/api/dependencies`: HTTP wiring, auth dependencies,
  status codes, and response models only.
- `app/services`: business logic and application workflows.
- `app/models`: SQLAlchemy models.
- `app/schemas`: Pydantic request and response schemas.
- `app/db/session.py`: engine, session factory, DB dependency.
- `app/core/config.py`: environment-driven configuration.
- `app/core/security.py`: password hashing and token helpers.
- `app/worker.py` and `app/core/job_queue.py`: background jobs.
- `alembic/versions/`: schema migrations.

## Rules

- Business logic MUST live in `app/services`.
- Route handlers MUST NOT contain SQLAlchemy queries or business rules.
- Services MUST NOT raise `HTTPException`.
- Auth dependencies MUST remain reusable and explicit.

## Dependencies

- MUST NOT add dependencies or change versions in `pyproject.toml` or `uv.lock`
  unless the user explicitly requested that dependency change.
- Prefer stdlib and packages already in the project.
- CI and pre-commit enforce `pyproject.toml` / `uv.lock` pairing. See
  `docs/ci-policy-guards.md`.
