# Agent Orchestration

Use this file at the **start of every non-trivial task**. It complements
tool-specific entry points (`AGENTS.md`, `CLAUDE.md`) and binding rules in other
`.ai-rules/` files.

## 0. Project identity

This repository is the **Appointment Voice SaaS** product
(`appointment-voice-saas`), not a generic template. When orienting, distinguish:

- **Inherited foundation** — generic FastAPI/auth/tenancy/worker/CI scaffolding
  (`app/`, `docs/foundation/`, `docs/template-*`, `TEMPLATE_FREEZE_CHECKLIST.md`).
- **AVS product docs** — `docs/product-scope.md`, `docs/domain-model.md`,
  `docs/appointment-saas-roadmap.md`, `ROADMAP.md`, `PROJECT_STATUS.md`.
- **AVS implementation** — product code, tests, and migrations implementing
  roadmap items (`AVS-Exxx`).
- **AI workflow/rules** — `.ai-rules/`, `AGENTS.md`, `CLAUDE.md`,
  `docs/ai-workflows.md`, `.commands/`, `agents/`.

For Appointment Voice SaaS product tasks, pick the next item from
`docs/appointment-saas-roadmap.md` (the executable backlog), not the
high-level `ROADMAP.md`, unless the user specifies otherwise.

## 1. Classify the task

| Type | Examples | Load first |
|------|----------|------------|
| Bug fix | Wrong status code, regression | `tdd-and-regression.md`, `context-map.md` |
| Feature | New endpoint, service workflow | `spec-driven-development.md`, `incremental-work.md` |
| Refactor | Rename, extract, no behavior change | `incremental-work.md`, `architecture.md` |
| Security | Auth, uploads, webhooks | `threat-modeling.md`, `security.md` |
| Infra | Docker, CI, Makefile | `docker.md`, `context-map.md` |
| Docs / status | README, ROADMAP, tracking files | `documentation.md`, `review.md` |
| Template clone | New product from this repo | `template-onboarding.md` |
| Roadmap / debt | ROADMAP.md or TECH_DEBT.md item | `planning-and-task-breakdown.md`, `incremental-work.md` |

## 2. Load relevant rules

- Read `.ai-rules/context-map.md` and open the listed files for this task type.
- Read binding rules that apply (architecture, testing, security, git, etc.).
- Optional: use a persona from `agents/` for review-only work (see
  `docs/ai-workflows.md`).

## 3. Define scope

- State the **objective** in one sentence.
- For Appointment Voice SaaS product tasks, name the affected layer(s): product
  docs/roadmap, domain model, booking backend, calendar integration, IVR/call
  flow, SMS notifications, business settings, admin/owner operations,
  infrastructure/CI, or AI workflow/rules.
- Classify the task kind for the completion report: docs-only, backend runtime,
  integration, CI/infra, or rules/workflow.
- List **in scope** and **out of scope** explicitly.
- Do not expand scope (no drive-by refactors, no unrelated docs, no P3 work
  unless requested).

## 4. Run the anti-overengineering check

Before adding files, dependencies, abstractions, or large rewrites, apply
`.ai-rules/anti-overengineering.md`:

- Can existing code or project patterns solve this?
- Can code be deleted or simplified instead of added?
- Is a new dependency, file, abstraction, or generic framework actually needed?
- Are security, validation, errors, tests, tenancy, and production safety still
  covered?

## 5. List assumptions

- Note defaults you are using (tenant model, env, API version `/api/v1`).
- If blocked on a product decision, ask **one** focused question; otherwise
  proceed with the smallest safe default and document it.

## 6. Pick validation commands

Choose validation based on which files changed. Run the **first** column for
fast feedback; run the **before PR** column when the change is non-trivial or
production-impacting.

| Change type | First (fast feedback) | Before PR |
|-------------|------------------------|-----------|
| Docs-only (no AI workflow files touched) | none required | — |
| AI workflow / `.ai-rules` files changed | `make validate-ai-workflows`; `make policy-guards` if commit/policy/CI-sensitive files also changed | none (do not run pytest unless runtime code also changed) |
| Application code (services, routes, schemas) | targeted pytest for the touched module, e.g. `pytest -k booking`, `pytest tests/test_<module>.py`, `pytest tests/api/...` | `make validate` if non-trivial or production-impacting |
| Migrations / models | relevant migration/model tests (`tests/test_migrations.py`, matching model tests); verify `alembic upgrade head` | `make validate` |
| Docker / CI / Makefile | most relevant local check (e.g. `bash scripts/ci/run_policy_guards.sh`, a local `docker compose build`); pytest alone does not validate these | `make policy-guards`; `make validate` if app code also changed |

### CI is the final gate

Targeted local tests give fast feedback during a slice. Full local validation
(`make validate`) is preferred before opening a PR for application/runtime
changes, but GitHub Actions CI remains authoritative — local validation does
not replace a green CI run before merge.

## 7. Execute incrementally

Follow `.ai-rules/incremental-work.md` and `.ai-rules/planning-and-task-breakdown.md`.

## 8. Report completion

For every non-trivial task that changes files, the Builder Agent MUST
automatically run the configured read-only Reviewer subagent before the final
response. Do not ask the user whether to run review, and do not require a second
user prompt, pasted handoff, local runner command, or separate CLI window.

- Codex CLI uses the `reviewer` subagent configured in
  `.codex/agents/reviewer.toml`.
- Claude Code uses the `code-reviewer` subagent configured in
  `.claude/agents/code-reviewer.md`.
- The Reviewer is read-only and must inspect the current git diff, untracked
  files, validation output, security and production risks, overengineering,
  tests, docs drift, and scope creep.
- The Builder must wait for the Reviewer result before final response.
- Read-only or trivial tasks may skip Reviewer, but MUST explicitly say
  `Reviewer skipped: <reason>`.
- `.commands/builder-handoff.md` remains the Builder handoff format when a
  structured handoff is needed; do not duplicate that template here.

Every task response MUST include the sections in **`.ai-rules/learning-mode.md`**
(for non-trivial file-changing tasks) and at minimum:

- **Files changed** (created / modified)
- **Tests / validation run** (exact commands and pass/fail)
- **Risks** (deployment, security, migration, compatibility)
- **Remaining work** (if any; do not invent follow-ups)
- **Builder summary** (what changed and why)
- **Reviewer verdict** (or explicit skip reason for read-only/trivial tasks)

See `learning-mode.md` for mentor sections: why each file, what calls it, what
could break, manual verification, interview-defense explanation.

## 9. Git workflow

Follow `.ai-rules/git.md`: no commit, push, merge, force-push, or branch delete
unless the user explicitly writes `approve`.

Before any commit:

1. Draft the exact subject and body (Conventional Commits).
2. Show or verify that message with the user when they requested a commit.
3. Confirm it contains **no** AI attribution trailers (`Co-authored-by: Cursor`,
   `Co-authored-by: Claude`, `Generated-by:`, `Created-by: AI`, etc.).
4. Run `bash scripts/ci/check_no_ai_commit_trailers.sh --message-file <file>`
   on the proposed message, or inspect `git log -1 --pretty=format:%B` after
   commit and before push.
5. Run `make policy-guards` before push when the branch includes new commits.

Install the commit-msg hook once per clone:
`uv run pre-commit install --hook-type commit-msg`.

### Auto-merge

See `.ai-rules/git.md` "Auto-Merge" — enabling auto-merge follows the same
explicit-approval model as push/merge and MUST NOT be used to bypass branch
protection, CI, or unresolved Reviewer findings.

## 10. Handoff and `/clear`

After completing a task, produce a compact handoff summary:

- Branch
- Commit(s)
- PR link (if any)
- Files changed
- Validation run (commands + pass/fail)
- Reviewer result
- Risks
- Next steps

`/clear` is a Claude Code session command, not a repository or git rule:

- Recommend `/clear` only before starting an **unrelated** task, to save tokens
  and avoid context contamination.
- Do not recommend `/clear` when the next task depends on the current context
  (e.g. continuing the same PR, addressing review feedback).
- Never claim `/clear` was executed — only the user can run it.
