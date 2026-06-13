# Context Map

Before editing, read the files listed for your **task type**. Start with
`.ai-rules/agent-orchestration.md`.

## Always read

| File | When |
|------|------|
| `.ai-rules/repository.md` | Every task |
| `.ai-rules/git.md` | Before commit/push/merge |
| `.ai-rules/context-map.md` | You're here — pick a row below |

## Task type → read list

### API / HTTP change
- `.ai-rules/api.md`, `.ai-rules/architecture.md`, `.ai-rules/testing.md`
- `app/api/routes/<module>.py`, `app/api/dependencies/`, `app/schemas/`
- `app/services/<module>_service.py`
- `tests/test_<module>.py` or `tests/test_*` for that area
- `app/api/v1.py` (router registration)
- `app/api/openapi.py` if error responses change

### Database / model change
- `.ai-rules/database.md`, `.ai-rules/testing.md`
- `app/models/`, `app/db/session.py`
- `alembic/versions/` (latest revisions)
- `tests/test_migrations.py`, `tests/test_ops_migrations.py`
- `scripts/ci/check_model_migration_pair.sh` policy

### Security / auth change
- `.ai-rules/security.md`, `.ai-rules/threat-modeling.md`, `.ai-rules/testing.md`
- `app/core/security.py`, `app/core/config.py` (production validators)
- `app/services/auth_service.py`, `app/api/routes/auth.py`
- `app/api/dependencies/auth.py`, `app/api/dependencies/rate_limit.py`
- `tests/test_auth.py`, `tests/test_access_token_revocation.py`, `tests/test_security_jwt.py`

### Tenancy change
- `.ai-rules/tenancy.md`, `.ai-rules/security.md`
- `app/core/tenant_context.py`, `app/api/dependencies/tenant.py`
- `app/services/tenant_*`, affected models with `tenant_id`
- `tests/test_tenant_isolation.py`, `tests/test_tenancy.py`
- `docs/tenant-isolation.md`

### Worker / queue change
- `.ai-rules/workers.md`, `.ai-rules/testing.md`
- `app/worker.py`, `app/core/job_queue.py`
- Related service invoked by worker
- `tests/test_worker.py`, `tests/test_job_queue.py`

### Storage / uploads change
- `.ai-rules/security.md`, `.ai-rules/architecture.md`
- `app/services/storage_service.py`, `app/core/file_validation.py`
- `app/api/routes/files.py`, `docs/file-upload-production.md`
- `tests/test_files.py`, `tests/test_storage_service.py`

### Docker / CI / Makefile change
- `.ai-rules/docker.md`, `.ai-rules/documentation.md`
- `Dockerfile`, `docker-compose*.yml`, `Makefile`
- `.github/workflows/`, `scripts/ci/`
- `docs/ci-policy-guards.md`

### Docs / project status change
- `.ai-rules/documentation.md`, `.ai-rules/review.md`
- `README.md`, `PROJECT_STATUS.md`, `ROADMAP.md`, `TECH_DEBT.md`
- Matching `docs/` topic file
- `TEMPLATE_FREEZE_CHECKLIST.md` if template-scope wording changes

### AI rules / workflow change
- `.ai-rules/documentation.md`, `docs/ai-workflows.md`
- `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/project.mdc`
- `scripts/validate-ai-workflows.sh`

### Template clone / onboarding
- `.ai-rules/template-onboarding.md`
- `docs/template-onboarding.md`, `docs/template-usage.md`
- `TEMPLATE_FREEZE_CHECKLIST.md`, `.env.example`

### Spec / ADR / design doc
- `.ai-rules/spec-driven-development.md`
- `docs/specs/README.md`, `docs/decisions/README.md`, `docs/adr/`

## Tracking files (do not confuse roles)

| File | Purpose |
|------|---------|
| `PROJECT_STATUS.md` | Verified capabilities only |
| `ROADMAP.md` | Planned prioritized work |
| `TECH_DEBT.md` | Debt register |
| `TEMPLATE_FREEZE_CHECKLIST.md` | Template reuse / freeze |
