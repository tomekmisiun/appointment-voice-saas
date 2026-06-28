# Configuration

Configuration is split between backend `.env`, frontend `.env.local`,
observability `.env.observability`, Docker Compose, Railway TOML files, and
GitHub Actions environment variables/secrets.

## Canonical Templates

| Area | Template/source |
|---|---|
| Backend API and worker | [`.env.example`](../../.env.example), [`app/core/config.py`](../../app/core/config.py) |
| Frontend | [`frontend/.env.example`](../../frontend/.env.example), [`frontend/lib/api/config.ts`](../../frontend/lib/api/config.ts) |
| Observability | [`.env.observability.example`](../../.env.observability.example), [`docker-compose.observability.yml`](../../docker-compose.observability.yml) |
| Local services | [`docker-compose.yml`](../../docker-compose.yml) |
| Production API | [`railway.api.toml`](../../railway.api.toml) |
| Production worker | [`railway.worker.toml`](../../railway.worker.toml) |
| Production frontend | [`frontend/railway.toml`](../../frontend/railway.toml) |
| CI/CD | [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml) |

## Backend Required Local Values

Copy the template from the repository root:

```bash
cp .env.example .env
```

At minimum, local development needs:

| Variable | Required | Default/example | Used by |
|---|---:|---|---|
| `DATABASE_URL` | Yes | `postgresql://app_user:app_password@db:5432/app_db` | API, worker, Alembic |
| `TEST_DATABASE_URL` | Yes for tests | `postgresql://app_user:app_password@test_db:5432/app_test_db` | pytest |
| `SECRET_KEY` | Yes | placeholder in template | JWT signing |
| `ENVIRONMENT` | Yes | `development` | runtime validators and defaults |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` | Yes | local Redis service | cache, rate limit, queues |
| `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` | Yes for upload flows | local MinIO defaults | file storage |

Use a strong local `SECRET_KEY`; do not commit `.env`.

## Production Validation

`app/core/config.py` rejects unsafe production settings. In production, local
Docker defaults are not accepted for database, Redis, S3 credentials, password
reset URLs, and webhook secrets. Production also requires trusted hosts and
malware scanning settings.

Important production-only or production-sensitive variables include:

| Variable | Purpose |
|---|---|
| `ENVIRONMENT=production` | Enables strict production validation. |
| `TRUSTED_HOSTS_ENABLED`, `TRUSTED_HOSTS` | Restricts host headers. |
| `RATE_LIMIT_TRUST_FORWARDED_HEADERS` | Required behind trusted Railway/proxy headers. |
| `WEBHOOK_SIGNATURE_SECRET` | Required for generic webhook verification in production. |
| `METRICS_REQUIRE_AUTH`, `METRICS_BEARER_TOKEN` | Protects `/metrics`. Defaults to auth required in production. |
| `UPLOAD_MALWARE_SCAN_ENABLED`, `UPLOAD_MALWARE_SCANNER_URL` | Required by production validators. |
| `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM` | Required outside local development. |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `TWILIO_VOICE_BASE_URL` | Required when real Twilio providers are used. |

## Frontend Values

Create `frontend/.env.local` from the frontend template:

```bash
cd frontend
cp .env.example .env.local
openssl rand -base64 32
```

| Variable | Required | Description |
|---|---:|---|
| `BACKEND_API_URL` | Yes | Server-only FastAPI base URL. |
| `SESSION_SECRET` | Yes | Base64 AES-256-GCM key for encrypted HttpOnly sessions. |
| `APP_ORIGIN` | Yes | Expected frontend origin for state-changing BFF route handlers. |
| `BFF_TRUST_FORWARDED_HEADERS` | No | Enables forwarded IP handling only behind a trusted proxy. |
| `TENANT_SLUG` | No | Login-only tenant slug override for non-default tenant deployments. |

Do not use `NEXT_PUBLIC_` for backend secrets or backend API credentials.

## Public Demo Values

Public demo support is implemented but disabled unless configured:

| Variable | Purpose |
|---|---|
| `PUBLIC_DEMO_ENABLED` | Enables `POST /api/v1/auth/demo`. |
| `PUBLIC_DEMO_USER_EMAIL` | Demo user to load; seeded by `make seed-demo`. |
| `PUBLIC_DEMO_BUSINESS_ID` | Demo business scope. |
| `AUTH_DEMO_RATE_LIMIT_LIMIT`, `AUTH_DEMO_RATE_LIMIT_WINDOW_SECONDS` | Rate limit for demo session creation. |

See [`public-demo.md`](../product/public-demo.md) for the security contract.

## Observability Values

The local observability stack uses `.env.observability` and
`docker-compose.observability.yml`. Grafana requires its own safe local admin
credentials in that file. See [`observability-production.md`](observability.md)
for metrics, alerts, and operational checks.

