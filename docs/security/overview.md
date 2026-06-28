# Security

This document summarizes the active security model. It complements
[`secret-management.md`](secret-management.md), [`tenant-isolation.md`](../architecture/tenant-isolation.md),
[`webhook-idempotency.md`](../architecture/webhook-idempotency.md), and [`public-demo.md`](../product/public-demo.md).

## Secret Handling

- Local secrets belong in `.env` and `frontend/.env.local`; neither should be
  committed.
- Safe placeholders live in [`.env.example`](../../.env.example) and
  [`frontend/.env.example`](../../frontend/.env.example).
- Production secrets are configured through Railway/GitHub environment secrets,
  not repository files.
- CI runs gitleaks through `.github/workflows/ci.yml`.

Never place real access tokens, passwords, private keys, webhook signing
secrets, Twilio credentials, SMTP credentials, or customer data in docs.

## Authentication And Sessions

| Surface | Mechanism |
|---|---|
| Backend API | Bearer JWT access tokens and refresh tokens. |
| Token invalidation | `User.token_version`. |
| Frontend | Encrypted HttpOnly session cookie storing backend token material server-side. |
| CSRF/origin checks | Next.js BFF validates state-changing requests against `APP_ORIGIN`. |
| Admin authorization | Runtime checks use `User.role`. |
| Per-business RBAC | `BusinessMembership.role` exists but is not yet wired into runtime authorization. |

## Tenant Isolation

- Product models carry `tenant_id`.
- Business-scoped routes use `business_id` and tenant-aware dependencies.
- Current debt remains around systematic per-route tenant-isolation enforcement
  in CI; see [`../TECH_DEBT.md`](../../TECH_DEBT.md).

## Webhooks

- Twilio voice/SMS webhooks use Twilio signature validation.
- Generic webhooks use timestamped signature verification when
  `WEBHOOK_SIGNATURE_SECRET` is configured.
- Webhook and provider ingress routes are rate-limited.
- Idempotency is documented in [`webhook-idempotency.md`](../architecture/webhook-idempotency.md).

## Public Demo

The public demo is read-only when enabled:

- `POST /api/v1/auth/demo` issues a demo session for the configured demo user.
- Demo access tokens carry `is_public_demo=true`.
- `DemoReadOnlyMiddleware` blocks mutating requests for public demo sessions.
- Demo users are protected from password reset flows.
- Demo rate limits are configured separately from normal login limits.

See [`public-demo.md`](../product/public-demo.md) and ADR 0009.

## File Uploads

- Uploads use S3-compatible presigned URLs.
- Local development uses MinIO.
- Production settings require malware scanning to be enabled and configured.
- Allowed content types and max upload sizes are configured in backend settings.

See [`file-upload-production.md`](../operations/runbooks/file-uploads.md) and
[`malware-scanning.md`](malware-scanning.md).

## Known Security Gaps

Active gaps are tracked in [`../TECH_DEBT.md`](../../TECH_DEBT.md), especially:

- per-business RBAC not wired into runtime auth,
- systematic tenant-isolation guard coverage not yet enforced in CI,
- SMS template injection risk if future user-editable templates are added,
- possible production/fresh-DB divergence around future staff invitation work.

Do not mark these resolved without matching runtime code, migrations if needed,
and tests.

