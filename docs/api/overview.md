# API

The backend is a FastAPI application. Generated OpenAPI is the source of truth
for exact request and response schemas.

## API Reference

| Reference | Location |
|---|---|
| Local Swagger UI | `http://localhost:8000/docs` |
| Local OpenAPI JSON | `http://localhost:8000/openapi.json` |
| Generated frontend copy | [`frontend/lib/api/openapi.json`](../../frontend/lib/api/openapi.json) |
| TypeScript schema | [`frontend/lib/api/schema.gen.ts`](../../frontend/lib/api/schema.gen.ts) |

Regenerate frontend API types from the repository root/frontend script:

```bash
cd frontend
pnpm api:generate
```

Check that generated API files are current:

```bash
cd frontend
pnpm api:check
```

## Route Prefixes

| Prefix | Purpose |
|---|---|
| `/api/v1` | Canonical product API. Registered in [`app/api/v1.py`](../../app/api/v1.py). |
| `/health` | Liveness, readiness, dependency health, and runtime checks. |
| `/metrics` | Prometheus metrics endpoint. Auth is required when `METRICS_REQUIRE_AUTH=true`. |
| legacy unversioned routes | Deprecated compatibility routes, only when `LEGACY_ROUTES_ENABLED=true`. |

## Authentication

- Protected API routes use Bearer JWT access tokens.
- Refresh tokens are rotated through backend auth endpoints.
- The Next.js frontend does not expose backend tokens to browser JavaScript; it
  stores them in an encrypted HttpOnly session cookie.
- Admin-only endpoints use role checks based on `User.role`.
- `BusinessMembership.role` is stored but is not yet the runtime authorization
  source.

## Main Route Groups

| Group | Examples | Notes |
|---|---|---|
| Auth | `/api/v1/auth/register`, `/api/v1/auth/token`, `/api/v1/auth/token/refresh`, `/api/v1/auth/demo` | Rate-limited. Demo requires public demo settings. |
| Signup/onboarding | `/api/v1/signup`, `/api/v1/onboarding` | Tenant signup is public and rate-limited; onboarding requires admin auth. |
| Business operations | `/api/v1/businesses`, nested staff/services/hours/exceptions/bookings | Tenant and business scoping are enforced by dependencies and service queries. |
| Availability | `/api/v1/businesses/{business_id}/availability` | Generates slots from business/staff schedules, exceptions, bookings, and blocks. |
| Clients/customers | nested business client/customer routes | CRM clients have CRUD and booking history. Customer API is more limited. |
| IVR simulator | `/api/v1/ivr/simulate/call`, `/api/v1/ivr/simulate/press` | Local/test simulator; no frontend simulator UI. |
| Twilio webhooks | `/api/v1/webhooks/twilio/voice`, `/api/v1/webhooks/twilio/voice/{session_id}`, `/api/v1/webhooks/twilio/sms/*` | Signature validation and rate limiting apply. |
| Generic webhooks | `/api/v1/webhooks/*` | HMAC/idempotency pattern for provider-style inbound events. |
| Files | `/api/v1/files/*` | S3-compatible presigned upload/download workflow. |
| Admin | `/api/v1/admin/*`, `/api/v1/admin/tenants/*`, `/api/v1/owner-leads/*` | Admin/platform management surfaces. |

Do not manually duplicate the full endpoint list in docs. Use OpenAPI for exact
method names, payloads, response models, and error schemas.

## Webhook Constraints

- Twilio Voice routing uses the webhook `To` field matched to `Business.phone`.
- Twilio keypress callbacks use `/api/v1/webhooks/twilio/voice/{session_id}`.
- Webhook idempotency is backed by Redis/database helpers depending on route.
- Production requires a strong `WEBHOOK_SIGNATURE_SECRET` for generic webhook
  verification and Twilio credentials when Twilio providers are enabled.

## Error Contract

OpenAPI documents shared error responses from [`app/api/openapi.py`](../../app/api/openapi.py).
Protected routes should expose the standard error envelope instead of leaking
implementation exceptions.

