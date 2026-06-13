# Security Rules

Production-ready mindset for all backend changes.

## Secrets

- MUST NOT hardcode secrets or commit credentials, API keys, certificates, SSH
  keys, database dumps, `.env`, or local database files.
- MUST NOT add production-like secrets to `app/core/config.py` defaults,
  `.env.example`, Docker files, or documentation. Use obvious placeholders only.
- If secrets are detected in changes, stop and warn the user.

## Auth And Sessions

- Authentication logic MUST stay explicit and reviewable.
- Authorization MUST be enforced at route and dependency boundaries.
- MUST NOT remove or disable auth, permission checks, rate limits, webhook
  signature verification, or tenant checks without explicit user request.
- If a security-control test fails, fix the implementation or test. MUST NOT
  delete the control to make tests pass.

## Production Config Validators

- MUST NOT weaken or bypass `validate_production_settings` or
  `validate_staging_settings` without explicit user request.

## API Safety

- Validate input through Pydantic schemas and FastAPI validation.
- Use correct HTTP status codes.

## Tenancy

- Tenant isolation rules live in `.ai-rules/tenancy.md` and MUST be followed
  for all tenant-owned data.
