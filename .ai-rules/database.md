# Database Rules

SQLAlchemy, Alembic, PostgreSQL, and a separate test database.

## SQLAlchemy

- Use SQLAlchemy consistently. Prefer SQLAlchemy 2.0 style in new code.
- Models MUST live in `app/models`.
- Database access MUST go through the existing session dependency.
- MUST NOT hardcode database credentials.

## Alembic

- Any schema change REQUIRES a new Alembic revision in `alembic/versions/`.
- MUST NOT modify existing migration files unless the user explicitly requested
  it.
- MUST NOT mix unrelated schema changes and refactors in one migration.
- CI enforces model changes → new migration. See `docs/ci-policy-guards.md`.

## Destructive Migrations

- MUST NOT drop columns or tables in the same release that removes application
  code. Use expand/contract across releases.
- MUST NOT use `op.drop_*` unless the user explicitly requested a breaking
  migration.
- CI flags destructive operations in new migration **`upgrade()`** blocks. See
  `docs/migration-rollback.md` and `docs/ci-policy-guards.md`.

## Data Access

- Keep queries explicit in services unless a dedicated repository pattern
  already exists in the touched area.
- Add indexes when adding filters, search, sorting, or foreign keys that need
  them.
