# Testing Rules

Use pytest for backend tests.

## Requirements

- New features MUST include tests.
- Every new endpoint MUST include tests.
- Bug fixes MUST include regression tests when behavior changed.
- Auth, permissions, migrations, Redis, rate limits, tenancy, workers, and
  important business rules MUST have tests when touched.
- MUST NOT break existing tests.

## Test Integrity

- MUST NOT delete or skip existing tests to make a change pass.
- New `@pytest.mark.skip` or `@pytest.mark.xfail` REQUIRES explicit user
  approval.

## Local Validation

- Run `make validate` before commit when changing application code, tests, or
  migrations. CI enforces the same coverage floor and test jobs.
- Pre-commit runs cheap hygiene checks only. See `docs/development/ci-policy.md`.

## Test Design

- Prefer focused pytest tests of observable behavior.
- Keep fixtures simple and explicit.
