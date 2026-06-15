# Pre-Merge Review

Use before opening or merging a PR. Optional deep dives: personas in `agents/`.

**Reviewer:** read `.ai-rules/review-checklist.md` + diff — not the full
`.ai-rules/` corpus. This file is the detailed reference for humans and Builder.

## Review iteration limit

- Max **2** reviewer → fix → reviewer cycles per task.
- Cycle 1: initial review after Builder handoff.
- Cycle 2: re-review after Builder addresses **Request changes** (or material diff change).
- After cycle 2, if blockers remain: **escalate to the user** — do not loop
  automatically. User decides waive, scope cut, or another manual review.

## Checklist

### Correctness
- [ ] Behavior matches spec / user request and acceptance criteria
- [ ] Edge cases handled (empty input, not found, inactive user, Redis down)

### Architecture
- [ ] Business logic in `app/services/`; routes thin
- [ ] Services use `DomainError`, not `HTTPException`
- [ ] No new circular imports or layer violations

### Tests
- [ ] New/changed behavior has tests
- [ ] `make validate` passes (or CI equivalent)
- [ ] No new skips without user approval

### Security
- [ ] Auth and permissions checked on new/changed protected routes
- [ ] No secrets in code, docs, or committed env files
- [ ] Production validators considered (`app/core/config.py`)

### Tenancy
- [ ] Queries filter by `tenant_id` where data is tenant-scoped
- [ ] JWT / header tenant cross-check unchanged or improved
- [ ] Cross-tenant denial tests when touching isolation paths

### Database / migrations
- [ ] Model change has Alembic revision (or documented bypass)
- [ ] No destructive migration without guard script approval
- [ ] Indexes/constraints considered for new query patterns

### Performance
- [ ] No unbounded queries (offset deep pages, full table scans without need)
- [ ] Cache invalidation path understood for list mutations

### Observability
- [ ] Errors use standard envelope; no leaked stack traces in production paths
- [ ] Metrics/logging unchanged or intentionally updated

### Docs / status
- [ ] README / docs updated if setup, API, env, or workflows changed
- [ ] `PROJECT_STATUS.md` only for **verified** capabilities
- [ ] `ROADMAP.md` / `TECH_DEBT.md` updated when closing items

### Git / commit hygiene
- [ ] No AI attribution trailers in any commit on the branch (`Co-authored-by:
  Cursor`, `Claude`, `Codex`, `Generated-by:`, `Created-by: AI`, etc.)
- [ ] `bash scripts/ci/check_no_ai_commit_trailers.sh` passes for the branch
  range (included in `make policy-guards`)

### Backward compatibility
- [ ] `/api/v1` contract preserved or breaking change documented
- [ ] Legacy routes unchanged unless explicitly gated

### Deployment risk
- [ ] Migrations required? Redis/S3 new deps? Env vars added to `.env.example`?

## Output format (review tasks)

```markdown
## Summary
<1–3 sentences>

## Findings
| Severity | File | Issue | Recommendation |
| Critical / High / Medium / Low | ... | ... | ... |

## Validation
<commands run + results>

## Verdict
Approve / Approve with nits / Request changes
```

Use `.commands/review-current-branch.md` for a copy-paste review prompt.
