> [!WARNING]
> Dokument archiwalny. Nie opisuje aktualnego źródła prawdy.
> Aktualna dokumentacja: [Documentation index](../../README.md).

# Inherited Foundation Template Onboarding

Appointment Voice SaaS is now the active product repository. This document is
inherited foundation reference material for understanding the original backend
template workflow. Active product status, roadmap, and debt live in the root
`PROJECT_STATUS.md`, `ROADMAP.md`, and `TECH_DEBT.md`.

Use this guide when starting a new project from this repository.

## What This Template Is

- A **production-oriented foundation** with P0, P1, and P2 roadmap work complete
  — auth, users, audit logs, Redis, workers, uploads, observability hooks, CI,
  and deployment scripts. Optional P3 improvements remain non-blocking.
- A **local/dev stack** with Docker Compose, pytest, migrations, and smoke
  checks.

## What This Template Is Not

- A finished multi-tenant SaaS platform (billing, invites, org membership, and
  provider-specific infra are downstream work).
- A one-click production deployment (you must choose hosting, secrets, backups,
  and runtime targets).

## 1. Clone Or Fork

```bash
git clone https://github.com/your-org/your-backend.git
cd your-backend
```

Or use GitHub **Use this template** / fork, then rename the remote and
repository settings.

## 2. Rename Project Metadata

Update at minimum:

| Item | Location |
|------|----------|
| Application name | `APP_NAME` / `settings.app_name` via env or `app/core/config.py` default |
| README title and links | `README.md` |
| Container image path | `.github/workflows/release.yml`, `deploy.yml`, `Makefile` `deploy-dry-run` |
| Default tenant slug (optional) | `make seed-tenant` / `app/seed_default_tenant.py` |
| Dev seed accounts | `app/seed_dev_data.py` — change emails before any shared staging |

Remove or replace example GHCR paths such as
`ghcr.io/example/fastapi-production-foundation/api`.

## 3. Configure Environment

```bash
cp .env.example .env
```

Set a strong `SECRET_KEY`. For shared staging/production, never use Docker
defaults for database, Redis, SMTP, or S3.

See:

- `.env.example`
- `docs/operations/deployment.md`
- `docs/security/secret-management.md`

## 4. Run Locally

Recommended first path (full stack):

```bash
make bootstrap
```

This runs Docker Compose, migrations, dev seed, and HTTP smoke checks.

Validation:

```bash
make validate
```

Equivalent manual steps:

```bash
make docker-up
make migration-upgrade
make seed      # development only
make smoke
```

Observability stack (optional):

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

## 5. Run Tests

```bash
make validate
```

CI also enforces `--cov-fail-under=85`. Use `make test-coverage` for the same
floor locally.

## 6. Configure Staging Deploy

1. Create GitHub Environments: `staging`, `production`.
2. Configure secrets/variables documented in `docs/operations/deployment.md`
   and the GitHub Environments checklist in
   `docs/operations/runbooks/production-runtime.md`.
3. Publish an image with a version tag:

   ```bash
   git tag v0.1.0 && git push origin v0.1.0
   ```

4. Run the manual **Deploy** workflow against `staging` with `dry_run=false`
   after secrets are set.

`docker-compose.prod.yml` assumes **managed** PostgreSQL, Redis, and S3 (or
equivalent) outside the compose file. It only runs `api` and `worker`
containers.

## 7. Production Decisions Checklist

Before accepting production traffic, decide and document:

- Hosting: Kubernetes, PaaS, VM + Compose, or other.
- Secret manager and rotation policy.
- Backup provider, RPO/RTO, and whether PITR is required.
- Tracing: Sentry only, OpenTelemetry, or both.
- Registration policy: public, invite-only, or disabled.
- Platform admin vs tenant admin model (`docs/architecture/tenant-isolation.md`,
  `docs/platform-admin-model.md`).
- Reverse proxy / TLS termination (`docs/operations/runbooks/production-runtime.md`)

Track project-specific choices in your own runbook. This template documents
patterns, not your provider accounts.

## 8. Where To Look Next

| Topic | Document |
|-------|----------|
| Template reuse / freeze | `docs/archive/legacy/template-freeze-checklist.md`, `docs/archive/legacy/template-usage.md` |
| AI rules and agent workflows | `docs/development/workflows/ai-workflows.md`, `AGENTS.md`, `.ai-rules/`, `agents/`, `.commands/` |
| Production deployment | `docs/operations/deployment.md` |
| Redis production contract | `docs/architecture/redis-production-contract.md` |
| Reverse proxy / runtime examples | `docs/operations/runbooks/production-runtime.md` |
| Secrets | `docs/security/secret-management.md` |
| Migrations / rollback | `docs/operations/runbooks/migration-rollback.md` |
| Backups | `docs/operations/backups/overview.md`, `docs/operations/backups/restore.md`, `docs/operations/backups/pitr.md` |
| Tenant isolation | `docs/architecture/tenant-isolation.md`, `docs/platform-admin-model.md` |
| Architecture decisions | `docs/adr/README.md` |
| Observability | `docs/operations/observability.md` |
| Load / concurrency | `docs/testing/load-and-concurrency.md`, `docs/architecture/scaling.md` |
| Troubleshooting | `docs/operations/troubleshooting.md` |
| Product implementation state | `PROJECT_STATUS.md` |
| Historical foundation implementation state | `docs/archive/legacy/template-project-status.md` |
