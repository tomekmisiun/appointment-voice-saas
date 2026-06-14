# Agent Orchestration

Use this file at the **start of every non-trivial task**. It complements
tool-specific entry points (`AGENTS.md`, `CLAUDE.md`) and binding rules in other
`.ai-rules/` files.

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

| Change type | Minimum validation |
|-------------|-------------------|
| Application code / tests / migrations | `make validate` |
| CI / scripts / policy only | `make policy-guards` and `make validate-ai-workflows` |
| Docs / AI rules only | `make validate-ai-workflows`; run `make validate` if docs claim test counts |
| Docker / Compose | `make validate` if app touched; else build smoke as needed |

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
