# Review Checklist (Reviewer Agent)

**Audience:** read-only Reviewer subagent only. Builder uses full `.ai-rules/`.

Read **this file only** (+ git diff via tools + Builder handoff). Load **at most
one** persona from `agents/` when the diff is narrow and domain-specific. Do
**not** load `.ai-rules/` source files or `.commands/two-agent-review.md`.

**Mode:** review only — no edits, commits, push, merge, or fixes.

## Handoff inputs (from Builder)

1. **Objective** — one sentence
2. **Files changed** — `git diff --name-status` (not full diff in handoff)
3. **Validation** — commands run + PASS/FAIL + brief evidence
4. **Summary** — 2–4 sentences; risks and focus areas as bullets

If incomplete, inspect repo directly and note gaps. **Do not expect** full
conversation history or pasted diff — run `git diff` locally.

## Instructions

1. Apply checklist sections below against the diff.
2. Cross-check docs/status if tracking files or README changed.
3. Verify validation results in handoff.
4. Check branch commits for AI attribution trailers (`make policy-guards`).
5. **Iteration limit:** max 2 reviewer passes per task; then escalate to user.

Review is **advisory** — CI and human approval remain the merge gate.

## Output format (required sections)

```markdown
## Blockers
<Issues that must be fixed before approval, or "None found">

## Should-fix
<Important issues that should be fixed in this change, or "None found">

## Nice-to-have
<Non-blocking improvements, or "None found">

## Validation concerns
<commands expected vs handoff results; gaps noted, or "None found">

## Security/production risks
<risks or "None found">

## Overengineering/scope creep
<risks or "None found">

## Final verdict
Approve / Approve with nits / Request changes
```

Be strict; cite file paths and evidence. Prefer **Request changes** when
security, tenancy, migration, or test gaps are material.

---

## Correctness

- [ ] Matches user request / spec / acceptance criteria
- [ ] Edge cases: empty input, not found, inactive user, Redis down

## Architecture & API

- [ ] Business logic in `app/services/`; routes thin (no SQL/business rules in routes)
- [ ] Services raise `DomainError`, not `HTTPException`
- [ ] No new circular imports or layer violations
- [ ] New endpoints under `/api/v1`; no new `legacy.py` routes unless requested
- [ ] Pydantic schemas for request/response; correct HTTP status codes
- [ ] No stack traces or internal details exposed to clients
- [ ] No new deps in `pyproject.toml` / `uv.lock` unless explicitly requested

## Tests & validation

- [ ] New/changed behavior has tests; every new endpoint tested
- [ ] Bug fixes include regression tests when behavior changed
- [ ] No deleted/skipped tests without user approval
- [ ] `make validate` run and passed (or CI equivalent noted)
- [ ] `make policy-guards` when CI/scripts/AI rules touched
- [ ] Auth, permissions, tenancy, migrations, Redis, workers touched → tests updated

## Security

- [ ] Auth/permissions on new/changed protected routes
- [ ] No secrets in code, docs, commits, `.env`, local DB files
- [ ] No real secrets in `config.py` defaults, `.env.example`, Docker — placeholders only
- [ ] Production/staging validators not weakened (`validate_production_settings`, etc.)
- [ ] Input validated at boundary (Pydantic/FastAPI)
- [ ] Webhook signatures, rate limits, upload limits intact if touched

## Tenancy

- [ ] Tenant-owned queries filter by `tenant_id` (never PK-only lookup)
- [ ] JWT / `X-Tenant-Slug` cross-check unchanged or improved
- [ ] Cross-tenant denial tests when isolation paths touched
- [ ] No cross-tenant endpoints without explicit platform-admin scope

## Database & migrations

- [ ] Model change → new Alembic revision in `alembic/versions/`
- [ ] No edits to existing migrations unless explicitly requested
- [ ] No destructive `op.drop_*` without explicit approval + guard script
- [ ] Indexes/constraints for new filters, FKs, search patterns
- [ ] No hardcoded DB credentials

## Workers & Redis (if touched)

- [ ] Unknown job types → failed/DLQ, not silent success
- [ ] Idempotency / ack / retry paths preserved
- [ ] No queue/key renames without migration note

## Docker / CI (if touched)

- [ ] Compose aligned with `app/core/config.py`; no prod secrets in Docker files
- [ ] No new Compose services without approval
- [ ] Prod runtime/CMD/CORS changes documented in `docs/production-deployment.md`

## Docs & status

- [ ] README / `docs/` updated if setup, API, env, or workflows changed
- [ ] `PROJECT_STATUS.md` only for **verified** capabilities
- [ ] `ROADMAP.md` / `TECH_DEBT.md` updated when closing items

## Git hygiene (branch under review)

- [ ] No AI attribution trailers in commit messages (`Co-authored-by: Cursor/Claude/Codex`, `Generated-by:`, etc.)
- [ ] `bash scripts/ci/check_no_ai_commit_trailers.sh` would pass

## Backward compatibility & deploy

- [ ] `/api/v1` contract preserved or breaking change documented
- [ ] New env vars in `.env.example`; migrations/Redis/S3 deps noted

## Overengineering & scope

- [ ] Smallest change that satisfies request; no drive-by refactors
- [ ] No unnecessary files, abstractions, dependencies, or generic frameworks
- [ ] Simplicity did not skip security, tenancy, validation, tests, migration safety

## Performance & observability (when relevant)

- [ ] No unbounded queries (deep offset, full scans without need)
- [ ] Cache invalidation understood for list mutations
- [ ] Standard error envelope; no leaked traces in production paths
