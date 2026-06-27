# VoxSlot Production Deployment

## Deployment flow

```
feature branch
    → Pull Request
    → CI (all jobs green)
    → merge to main
    → CI on main (all jobs green)
    → deploy-production job
    → railway up → api, worker, frontend deployed to Railway
```

No manual step is required after merge to `main`. If any required CI job fails, the `deploy-production` job is skipped and production is not touched.

---

## Railway services

| Service | URL | Config source | Builder | Start command | Migrations |
|---|---|---|---|---|---|
| `api` | `api-production-52a1.up.railway.app` | `railway.api.toml` → `railway.toml` at deploy time | Dockerfile (`target: production`) | `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers` | `alembic upgrade head` (preDeployCommand) |
| `worker` | — (internal) | `railway.worker.toml` → `railway.toml` at deploy time | Dockerfile (`target: production`) | `python -m app.worker` | none |
| `frontend` | `voxslot.up.railway.app` | `frontend/railway.toml` (uploaded as archive root via `--path-as-root`) | Nixpacks (auto-detects Next.js from `package.json`) | `pnpm start` | none |
| `Postgres` | — | — | Railway plugin | — | — |
| `Redis` | — | — | Railway plugin | — | — |

**Do not deploy `Postgres` or `Redis`** — these are Railway-managed plugins, not application services.

---

## Required secret

Add this once to the GitHub repository:

1. Open Railway dashboard → project **appointment-voice-saas** → **Settings** → **Tokens**.
2. Create a **Project Token** scoped to the **production** environment.
3. Open GitHub → repository → **Settings** → **Secrets and variables** → **Actions**.
4. Create a repository secret:
   - **Name:** `RAILWAY_TOKEN`
   - **Value:** the token from step 2

The `deploy-production` job exits with an error if `RAILWAY_TOKEN` is missing or empty.

---

## Railway dashboard settings (manual checklist)

These settings must be configured manually in the Railway dashboard once and do not change per deployment.

### All application services (api, worker, frontend)

| Setting | Required value |
|---|---|
| **Source Repo** | `tomekmisiun/appointment-voice-saas` |
| **Branch** | `main` |
| **Auto Deploy** | **OFF** — deployments are triggered by GitHub Actions `railway up`, not Railway's own git watcher |
| **Wait for CI** | **OFF** — CI completion is already enforced by `needs:` in the GitHub Actions workflow |

> Leaving **Auto Deploy ON** while this workflow is active causes double deployments on every merge to `main`.

### Service-specific Railway settings

| Service | Root Directory | Config File Path |
|---|---|---|
| `api` | `.` (repository root) | *(leave blank — CI copies `railway.api.toml` → `railway.toml` before upload)* |
| `worker` | `.` (repository root) | *(leave blank — CI copies `railway.worker.toml` → `railway.toml` before upload)* |
| `frontend` | `frontend` | *(leave blank — CI uses `--path-as-root`, uploading `frontend/` as archive root so `frontend/railway.toml` becomes `railway.toml`)* |

**How Railway v5 CLI reads config:** Railway CLI v5 removed the `--config` flag. Instead, each deploy step copies the service-specific toml to `railway.toml` in the working directory (for api/worker) or uses `railway up frontend/ --path-as-root` (for frontend, where `frontend/railway.toml` appears as `railway.toml` at the archive root). After upload, `railway.toml` is deleted from the workspace.

**Why config files use non-default names (`railway.api.toml`, `railway.worker.toml`):** Prevents Railway's git-based auto-discover from picking up the wrong config if Auto Deploy is ever re-enabled from the dashboard.

> If you re-enable Railway's GitHub integration in the future, set Config File Path in the dashboard to `railway.api.toml`, `railway.worker.toml`, and *(blank for frontend, Root Directory = `frontend`)* respectively.

---

## Database migrations

Migrations run exactly once per deployment via Railway's `preDeployCommand` in `railway.api.toml`:

```toml
preDeployCommand = "alembic upgrade head"
```

Railway runs this command inside the new API container before traffic is shifted. The `worker` and `frontend` services do not run migrations.

**Do not add a separate migration step to the GitHub Actions workflow** — Railway handles it server-side. Running migrations in both places creates a race condition.

---

## How `railway up` works

| Command | Effect |
|---|---|
| `railway up --service=<name> --ci` | Uploads source + `railway.toml`, triggers build, streams logs, waits for deploy (api) |
| `railway up --service=<name> --ci --detach` | Uploads source, triggers build and deploy, returns immediately (worker, frontend) |
| `railway up <path>/ --path-as-root --service=<name> --ci --detach` | Uploads `<path>/` as archive root — used for frontend so `frontend/railway.toml` is found as `railway.toml` |
| Railway **redeploy** (dashboard button) | Re-deploys the last uploaded source without rebuilding |
| Railway **restart** (dashboard button) | Restarts the running container without any build step |

`--detach` means the GitHub Actions job exits after submitting the deployment — it does not wait for Railway to finish building. Check the Railway dashboard to confirm deployment health.

---

## Deployment verification

After a merge to `main`:

1. Go to the GitHub Actions run and confirm `deploy-production` is green.
2. Open the Railway dashboard → **appointment-voice-saas** project → check that `api`, `worker`, and `frontend` all show a new deployment in progress or completed.
3. Verify:
   - `GET https://api-production-52a1.up.railway.app/health/live` → `200`
   - `GET https://api-production-52a1.up.railway.app/health/ready` → `200`
   - `GET https://voxslot.up.railway.app/` → frontend loads

---

## Rollback procedure

### Application rollback (no schema change)

1. Open Railway dashboard → affected service → **Deployments**.
2. Find the previous successful deployment.
3. Click **Redeploy** on that deployment.

### Application rollback (schema change involved)

1. Identify whether the migration is reversible (check `alembic/versions/`).
2. If reversible: connect to Railway's Postgres and run `alembic downgrade -1`.
3. Redeploy the previous application image via Railway dashboard.
4. Document the incident.

> Prefer forward-fix migrations over downgrades in production. See `docs/migration-rollback.md`.

---

## First-time setup procedure

1. Add `RAILWAY_TOKEN` secret to GitHub (see **Required secret** above).
2. Set **Auto Deploy = OFF** and **Wait for CI = OFF** for `api`, `worker`, `frontend` in Railway dashboard.
3. Verify Root Directory and Config File Path are correct for each service (see table above).
4. Merge any branch to `main` and watch the `deploy-production` job in GitHub Actions.

---

## Environment variables required in Railway

These must be set in the Railway production environment for each service. They are **not** stored in the repository.

### api and worker

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Railway injects automatically if using Railway Postgres) |
| `REDIS_URL` | Redis connection string (Railway injects automatically if using Railway Redis) |
| `SECRET_KEY` | Long random string (≥ 64 chars) |
| `ENVIRONMENT` | `production` |
| `TRUSTED_HOSTS` | Production API domain |
| `CORS_ALLOW_ORIGINS` | Frontend domain(s) |
| `PUBLIC_DEMO_ENABLED` | `true` to enable read-only demo mode |
| `PUBLIC_DEMO_USER_EMAIL` | Email of the seeded demo user |
| `PUBLIC_DEMO_BUSINESS_ID` | Primary key of the demo business |

### frontend

| Variable | Description |
|---|---|
| `BACKEND_API_URL` | Internal Railway URL of the `api` service |
| `SESSION_SECRET` | Long random string for encrypted session cookies |
| `APP_ORIGIN` | Public frontend URL (`https://voxslot.up.railway.app`) |
| `BFF_TRUST_FORWARDED_HEADERS` | `true` when running behind Railway's proxy |

---

## Existing `deploy.yml` workflow

`.github/workflows/deploy.yml` is a **legacy manual workflow** (template artifact). It supports SSH/deploy-hook based promotion of GHCR images and is retained as an emergency fallback.

It is **not** used for Railway deployments and does not conflict with `railway up` — it is `workflow_dispatch` only and requires `DEPLOY_HOOK_URL` or `DEPLOY_SSH_HOST` secrets that are not configured for Railway.

Do not remove it without verifying no staging or emergency deployment process depends on it.
