> [!WARNING]
> Dokument archiwalny. Nie opisuje aktualnego źródła prawdy.
> Aktualna dokumentacja: [Documentation index](../../README.md).

# Inherited Foundation Template Usage

Appointment Voice SaaS is now the active product repository. This file is
inherited foundation reference material, not the active product roadmap or
status.

Quick reference for using this repository as a **cloneable backend foundation**.
It is not a finished product; add your own domain modules and infrastructure
choices in the fork.

## Start Here

| Goal | Document |
|------|----------|
| First clone → local API running | `docs/archive/legacy/template-onboarding.md` |
| Freeze / reuse decision | `docs/archive/legacy/template-freeze-checklist.md` |
| Historical foundation features | `docs/archive/legacy/template-project-status.md` |
| Historical foundation future work | `docs/archive/legacy/foundation-template-roadmap.md`, `docs/archive/legacy/template-tech-debt.md` |
| Active product status | `PROJECT_STATUS.md` |

## Clone → Run (Minimum)

```bash
git clone <your-fork-url> example-app
cd example-app
cp .env.example .env
# Edit SECRET_KEY
make bootstrap
make validate
```

`make bootstrap` starts Docker Compose, runs migrations, seeds the default
tenant, loads dev users, and runs HTTP smoke checks.

## Rename Checklist (example-app)

| Item | Where |
|------|-------|
| Project title | `README.md` |
| App name (optional) | `APP_NAME` env or `app/core/config.py` default |
| Dev seed emails | `app/seed_dev_data.py` |
| Deploy dry-run image example | `Makefile` `deploy-dry-run` target |
| GHCR image path | Automatic from `GITHUB_REPOSITORY` in release/deploy workflows |

Release and deploy workflows use `ghcr.io/<owner>/<repo>/api` from the GitHub
repository name. No hardcoded org name is required for CI/CD to work in your
fork.

## Production Path

1. Read `docs/operations/deployment.md` and `docs/operations/runbooks/production-runtime.md`.
2. Set `ENVIRONMENT=production` with validated secrets (see
   `docs/archive/legacy/template-freeze-checklist.md` -> Required Environment
   Variables).
3. Override API process model if needed (multi-worker Uvicorn, Gunicorn, or
   horizontal replicas).
4. Deploy `api` + `worker` via `docker-compose.prod.yml` or your orchestrator.
5. Run migrations before traffic; enable smoke checks in the deploy workflow.

## Extend the Template

Add product features using the standard layers:

```
app/models/     → app/schemas/     → app/services/     → app/api/routes/
         ↘ alembic/versions/                    ↘ app/api/v1.py (register router)
```

- Put business rules in **services**; use **domain errors** (`app/core/domain_errors.py`).
- Enforce permissions via `require_permission` and tenant helpers.
- Write tests in `tests/`; keep `make validate` green.

Do not expand the template with product-specific modules (billing, bookings,
etc.) in the upstream freeze — add those only in your fork.

## What Not to Expect

See **What Is Intentionally Not Included** in
`docs/archive/legacy/template-freeze-checklist.md`.
The template gives auth, users, tenancy hooks, workers, uploads, webhooks,
observability boundaries, and CI — not a complete SaaS.
