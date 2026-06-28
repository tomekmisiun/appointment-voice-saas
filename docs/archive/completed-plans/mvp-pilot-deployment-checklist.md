> [!WARNING]
> Dokument archiwalny. Nie opisuje aktualnego źródła prawdy.
> Aktualna dokumentacja: [Documentation index](../../README.md).

# MVP Pilot Deployment Checklist (AVS-J006)

Pre-launch checklist for the first real pilot of Appointment Voice SaaS.
Work through each section top-to-bottom. Check off items as you complete them.

---

## 1. Environment & Infrastructure

- [ ] PostgreSQL instance provisioned (not shared with staging/dev).
- [ ] Redis instance provisioned (separate from staging).
- [ ] S3-compatible bucket provisioned for backups.
- [ ] Container registry image pushed (`ghcr.io/<org>/appointment-voice-saas/api:<tag>`).
- [ ] API process and Worker process are separate systemd/container units.
- [ ] Health check endpoint responds: `GET /health/ready` → `{"status":"ok"}`.
- [ ] TLS termination in front of API (HTTPS only).

## 2. Secrets

- [ ] `SECRET_KEY` is long (≥64 chars), random, stored in secret manager — not in `.env`.
- [ ] `DATABASE_URL` points to production PostgreSQL.
- [ ] `REDIS_URL` points to production Redis.
- [ ] `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` set (or `SMS_PROVIDER=fake` for pilot without real SMS).
- [ ] `GOOGLE_CALENDAR_SERVICE_ACCOUNT_JSON` set (or `CALENDAR_PROVIDER=fake` for pilot without real calendar).
- [ ] No committed `.env` files with real values.

## 3. Provider Configuration

- [ ] **SMS**: Set `SMS_PROVIDER=twilio` for real messages, or `SMS_PROVIDER=fake` to log only.
- [ ] **Calendar**: Set `CALENDAR_PROVIDER=google` for real sync, or `CALENDAR_PROVIDER=fake` to log only.
- [ ] **IVR / Voice**: Twilio phone number configured to forward to `/api/v1/ivr/` webhook (when real Twilio flow is implemented) — or use `/api/v1/ivr/simulate/*` for manual demo.
- [ ] Pilot business has a Twilio number purchased and assigned if going live.

## 4. Migrations

- [ ] `alembic upgrade head` run against production DB before first deploy.
- [ ] No pending migration heads (`alembic heads` shows a single head).
- [ ] Migration rollback procedure tested on a restore of the production DB (`make db-restore-check`).

## 5. Seed Data

- [ ] `make seed-tenant` run (creates `default` tenant).
- [ ] `make seed` run (creates `admin@example.local` — **change password immediately**).
- [ ] `make seed-demo` run (creates Glamour Studio Demo, or replace with real business via API).
- [ ] Admin password changed via `/api/v1/auth/password-reset` or direct DB update.

## 6. Worker

- [ ] Worker process running: `python -m app.worker`.
- [ ] Worker connects to same Redis as API.
- [ ] Failed job handling: `python -m app.worker_failed_jobs` scheduled (e.g., cron daily).
- [ ] Redis persistence enabled (AOF or RDB) — job loss on restart is unacceptable.

## 7. Backup & Restore

- [ ] `scripts/db_backup.sh` scheduled (daily minimum).
- [ ] `make db-restore-check` passed at least once against a real dump.
- [ ] S3 bucket versioning or retention policy configured.
- [ ] Backup notification/alerting enabled (see `docs/operations/backups/overview.md`).

## 8. Monitoring & Alerting

- [ ] Prometheus metrics scraped from `/metrics`.
- [ ] Alerts configured for: API error rate >1%, worker queue depth >100, health check failure.
- [ ] Structured logs forwarded to log aggregator.
- [ ] On-call rotation or alert recipient defined.

## 9. Security

- [ ] `ENVIRONMENT=production` set (enables production-only validators and security headers).
- [ ] Rate limiting active (Redis-backed; verify with `make smoke` after deploy).
- [ ] `CORS_ALLOWED_ORIGINS` set to known frontend domain(s) only.
- [ ] Trivy image scan passes with no HIGH/CRITICAL CVEs (`docker-build` CI job).
- [ ] No debug endpoints enabled in production.

## 10. Smoke Test

- [ ] `make smoke` (or `API_BASE_URL=<prod> make smoke`) passes after deploy.
- [ ] IVR simulate call returns 201 with `action=CONTINUE`.
- [ ] IVR press 2 returns `action=TRANSFER` with correct destination.
- [ ] Booking creation returns 201.
- [ ] Cancellation returns 200 with `status=cancelled`.

## 11. Rollback Plan

- [ ] Previous image tag noted (for `docker pull <prev-tag>` + `make migration-downgrade` if needed).
- [ ] Database dump taken immediately before deploy.
- [ ] Rollback procedure: swap image tag → re-deploy → run downgrade migration if schema changed.
- [ ] Team member with DB access available during deploy window.

---

## Go/No-Go

All 10 sections checked → pilot can go live.

Missing items in sections 2 (Secrets) or 8 (Monitoring) → **block launch** until resolved.

Missing items in sections 3 (Providers) → acceptable if using fake providers for initial demo.
