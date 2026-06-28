# Secret Management Runbook

This template keeps secrets environment-driven. Real projects should provide
secret values through the deployment platform or a dedicated secret manager, not
through committed files.

## Secret Inventory

Application secrets and sensitive values:

- `SECRET_KEY`: signs JWT access tokens, refresh tokens, and password reset
  token hashes.
- `DATABASE_URL`: contains PostgreSQL credentials and network location.
- `TEST_DATABASE_URL`: used only for automated tests and local validation.
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`: not always secret by themselves, but
  may be paired with provider credentials in real deployments.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`: email delivery
  configuration.
- `EMAIL_FROM`: not secret, but environment-specific.
- `PASSWORD_RESET_URL`: not secret, but must point to the correct frontend or
  API reset flow for the environment.
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`,
  `S3_BUCKET_NAME`, `S3_REGION_NAME`: object storage configuration and
  credentials.
- Grafana/observability credentials from `.env.observability` for local use.

Do not commit real values for any of these settings.

## Environment Separation

Use separate secrets for every deployed environment:

- local development
- CI/test
- staging
- production

Rules:

- Staging must not share production database, Redis, S3 bucket, SMTP
  credentials, or `SECRET_KEY`.
- CI/test secrets must be disposable and must never grant access to staging or
  production resources.
- Production secrets must live outside the repository in a secret manager or
  deployment-platform secret store.
- `.env.example` must contain only safe placeholders.

## Normal Rotation

Use this process for planned rotation:

1. Identify the secret, owning system, and affected services.
2. Create the new secret in the secret manager.
3. Update staging first.
4. Restart or redeploy staging services that consume the secret.
5. Run staging smoke checks:
   - `GET /health/ready`
   - login or another authenticated flow
   - password reset request if email credentials changed
   - file upload if S3 credentials changed
   - worker startup if Redis or database credentials changed
6. Update production secret values.
7. Redeploy or restart affected production services.
8. Run production smoke checks.
9. Revoke the old secret after the new value is confirmed working.
10. Record the rotation date and owner.

## Emergency Rotation

Use emergency rotation when a secret is leaked or suspected to be compromised:

1. Stop exposing the compromised value immediately.
2. Rotate the secret in the provider or secret manager.
3. Redeploy affected services with the new secret.
4. Revoke the old secret as soon as the new value is active.
5. Review logs for suspicious activity.
6. Rotate related credentials if lateral movement is possible.
7. Document the incident and follow-up actions.

## `SECRET_KEY` Rotation

`SECRET_KEY` is security-critical. It signs:

- access tokens
- refresh tokens
- password reset token hashes

Current behavior:

- Rotating `SECRET_KEY` invalidates existing JWT access tokens.
- Rotating `SECRET_KEY` invalidates existing refresh tokens because they can no
  longer be decoded.
- Existing password reset links become invalid because stored reset token
  hashes were derived from the old key.

Operational impact:

- Users may need to log in again.
- In-flight password reset links should be considered expired.
- For emergency compromise, forced reauthentication is acceptable.

Future improvement:

- Add key identifiers and a key-ring strategy if smooth secret rotation without
  invalidating all active sessions becomes a requirement.

## Database Credentials

Database credential rotation should be coordinated with connection pool
behavior:

1. Add or rotate credentials in the database provider.
2. Update the deployment secret.
3. Restart API and worker processes so new connections use the new credential.
4. Verify readiness checks.
5. Revoke old credentials after active connections drain.

Avoid changing database credentials during schema migrations unless the release
requires it.

## Email Credentials

SMTP credential rotation affects password reset email delivery.

After rotation:

- send a password reset request in staging
- verify the worker processes the job
- verify no real emails are sent from tests
- inspect worker logs for delivery failures

## Object Storage Credentials

S3 credential rotation affects file uploads.

After rotation:

- upload a small allowed file in staging
- verify metadata is persisted in PostgreSQL
- verify the object exists in the expected bucket
- revoke old keys only after the new keys are confirmed

## Local Files

Ignored local files may contain development-only values:

- `.env`
- `.env.observability`

These files must remain untracked. If a real secret is committed, stop work,
rotate the secret, remove it from history using an approved process, and notify
the project owner.
