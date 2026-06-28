# CI And Pre-Commit Policy Guards

This document lists checks enforced in CI and pre-commit. Judgment rules that
automation cannot enforce stay in `.ai-rules/`.

**Note:** Guards are exercised locally via `make policy-guards` and pre-commit,
but the first pull request that includes these scripts is the final proof that
they behave correctly against real GitHub base-branch diffs and workflow wiring.

## CI (`scripts/ci/run_policy_guards.sh`)

Run locally with:

```bash
make policy-guards
```

On pull requests, guards compare `origin/<base>...HEAD`. On pushes to `main`,
they compare against the previous commit.

### AI workflow file presence

`scripts/validate-ai-workflows.sh` verifies required agent workflow files
(`.ai-rules/` workflow rules, `agents/`, `.commands/`, `docs/development/workflows/ai-workflows.md`).

Run locally with:

```bash
make validate-ai-workflows
```

Included in `make policy-guards`.

### No AI attribution in commit messages

`scripts/ci/check_no_ai_commit_trailers.sh` scans commit messages in the checked
range (`origin/<base>..HEAD` on pull requests; `GITHUB_EVENT_BEFORE..HEAD` on
push to `main`; locally `origin/main..HEAD` when available).

Fails when any commit message contains AI attribution trailers, including:

- `cursoragent@cursor.com`
- `Co-authored-by: Cursor` / `Claude` / `Codex` (and similar agent names)
- `Authored-by:` lines naming agent tools
- `Generated-by:` / `Created-by: AI`

**Local checks:**

```bash
make policy-guards
bash scripts/ci/check_no_ai_commit_trailers.sh --message-file /path/to/msg
bash scripts/ci/check_no_ai_commit_trailers.sh --commit HEAD
```

Pre-commit commit-msg hook uses the same patterns when installed. Agents MUST
verify the exact commit message before committing (see `.ai-rules/git.md`).

**Bypass:** none.

### Model change requires migration

If any file under `app/models/` changes, the PR must add a new file under
`alembic/versions/*.py`.

**Bypass:** update `scripts/ci/allow-no-migration` in the same PR with a
one-line reason (non-schema-only model change), or set `CI_ALLOW_NO_MIGRATION=1`
in a workflow (maintainers only).

### pyproject.toml requires uv.lock

If `pyproject.toml` changes, `uv.lock` must change in the same diff (and vice
versa).

**Bypass:** none. Run `uv lock`.

### Dangerous migration operations

New migrations must not contain these in **`upgrade()`** (downgrade rollbacks
may use `op.drop_*` without an override):

- `op.drop_column`
- `op.drop_table`
- `op.drop_index`
- `op.execute("DROP` or `op.execute('DROP`

**Bypass:** update `scripts/ci/allow-migration-drops` in the same PR with a
one-line reason when `upgrade()` intentionally drops schema, or set
`CI_ALLOW_MIGRATION_DROPS=1` in a workflow (maintainers only).

### CI gate regression

Workflow changes must not weaken:

- pytest coverage floor (`--cov-fail-under=85`)
- Trivy CRITICAL/HIGH blocking (`exit-code: "1"`)
- required `test` job
- `docker-build` dependency on `test`
- dependency vulnerability gate (`pip-audit` job in `dependency-review.yml`,
  must not be `continue-on-error`)

**Bypass:** restore the guard or get explicit maintainer approval with rationale
in the PR description.

### Secrets scan

The `secrets-scan` job runs [gitleaks](https://github.com/gitleaks/gitleaks)
on every PR and push to `main`.

### Dependency vulnerability scan

The `pip-audit` job (`.github/workflows/dependency-review.yml`) exports the
`uv.lock` runtime dependencies and runs
[pip-audit](https://github.com/pypa/pip-audit) against them on every PR.
`actions/dependency-review-action` is not used because it requires GitHub
Advanced Security, which is not enabled on this (private) repo.

## Pre-commit (cheap local checks)

Install hooks once:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

Hooks enforce:

- Ruff lint/format fixes
- no committed `.env` files (`.env.example` is allowed)
- private key detection
- staged `pyproject.toml` / `uv.lock` pairing
- no AI authorship trailers in commit messages (when commit-msg hook installed;
  same patterns as `scripts/ci/check_no_ai_commit_trailers.sh`)

Pre-commit does **not** run pytest, Docker builds, or migrations.

## Policy-only rules (`.ai-rules/`)

Examples that remain human/agent judgment:

- tenant isolation query patterns
- auth and permission boundaries
- API versioning and legacy route policy
- service/route layering
- expand/contract migration strategy
- worker/DLQ semantics beyond pattern matching
- Redis rename compatibility planning
- production runtime safety
- documentation honesty and tracking-file discipline
- git push/merge/force-push without explicit user approval

## Full validation before commit

When changing application code, tests, or migrations:

```bash
make validate
```

This runs Ruff and pytest with the same 85% coverage floor as CI.
