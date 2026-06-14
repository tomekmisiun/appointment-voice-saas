# AI Workflows

How AI tooling should use this repository's rules, personas, and commands.

## Layers

| Layer | Location | Binding? | Purpose |
|-------|----------|----------|---------|
| **Project rules** | `.ai-rules/` | **Yes** | Architecture, security, testing, git, docs, anti-overengineering — must follow |
| **Codex entry index** | `AGENTS.md` | Pointer only | Codex CLI entry; points to `.ai-rules/` |
| **Claude Code entry index** | `CLAUDE.md` | Pointer only | Claude Code CLI entry; points to `.ai-rules/` |
| **Cursor wrappers** | `.cursor/rules/*.mdc` | Pointer only | Cursor entry; points to `.ai-rules/` and must not duplicate rule bodies |
| **Workflow rules** | `.ai-rules/agent-orchestration.md`, etc. | **Yes** | How to start tasks, plan, review, onboard |
| **Personas** | `agents/` | Optional | Review lenses (backend, security, tenancy, …) |
| **Commands** | `.commands/` | Optional | Copy-paste prompts for spec/plan/review/onboard |
| **Specs** | `docs/specs/` | Optional | Larger feature specs before implementation |
| **ADRs** | `docs/adr/` | Reference | Recorded architecture decisions |

## Start every task

1. Read `.ai-rules/agent-orchestration.md`
2. Use `.ai-rules/context-map.md` to open relevant binding rules and code paths
3. Always include `.ai-rules/anti-overengineering.md` before adding files,
   dependencies, abstractions, or large rewrites.
4. For non-trivial work: `.ai-rules/spec-driven-development.md` →
   `.ai-rules/planning-and-task-breakdown.md` → `.ai-rules/incremental-work.md`
5. Before merge: `.ai-rules/review.md`

## Tool Entry Points

| Tool | Entry point | Anti-overengineering source |
|------|-------------|-----------------------------|
| Cursor | `.cursor/rules/project.mdc` | `.ai-rules/anti-overengineering.md` |
| Codex CLI | `AGENTS.md` | `.ai-rules/anti-overengineering.md` |
| Claude Code CLI | `CLAUDE.md` | `.ai-rules/anti-overengineering.md` |

## Two-agent review (Builder + Reviewer)

For non-trivial branches, split **implementation** and **review** across two
agent sessions:

1. **Builder Agent** — implements on a feature branch, runs validation, then
   outputs handoff via **`.commands/builder-handoff.md`** (objective, changed
   files, diff, validation, impact sections).
2. **Reviewer Agent** — fresh session; paste this handoff plus
   **`.commands/two-agent-review.md`**. Reviews only; does not edit code unless
   explicitly asked.

Full workflow: **`docs/two-agent-review-workflow.md`**.

AI review is advisory; CI, tests, branch protection, and human approval remain
the merge gate.

## Common commands (copy from `.commands/`)

| Goal | File |
|------|------|
| Write a spec | `.commands/spec.md` |
| Break into tasks | `.commands/plan.md` |
| Implement next roadmap item | `.commands/build-next-roadmap-task.md` |
| Pre-PR review | `.commands/review-current-branch.md` |
| Two-agent handoff (Builder) | `.commands/builder-handoff.md` — pairs with Reviewer command below |
| Two-agent review (Reviewer) | `.commands/two-agent-review.md` |
| Security audit | `.commands/security-audit.md` |
| Clone for new product | `.commands/template-onboard.md` |
| Sync tracking docs | `.commands/update-project-status.md` |

## Personas (review only)

| Persona | File |
|---------|------|
| Backend / FastAPI | `agents/backend-reviewer.md` |
| Security | `agents/security-auditor.md` |
| Tenancy | `agents/tenancy-reviewer.md` |
| Database / migrations | `agents/database-reviewer.md` |
| Docker / CI | `agents/devops-ci-reviewer.md` |
| Template clone | `agents/template-onboarding-agent.md` |

Personas **do not override** `.ai-rules/`. They add focus for review tasks.

## Validation

| Change | Command |
|--------|---------|
| App / tests / migrations | `make validate` |
| CI policy scripts | `make policy-guards` |
| AI workflow file presence | `make validate-ai-workflows` |

## Commit messages (agents)

AI assistants MUST NOT add attribution trailers to commits. Before committing:

1. Read `.ai-rules/git.md` (forbidden trailers and verification steps).
2. Show or verify the exact subject + body with the user when they requested a
   commit.
3. Run `bash scripts/ci/check_no_ai_commit_trailers.sh --message-file <file>`
   on the proposed message, or run `make policy-guards` before push.
4. Install commit-msg hook once: `uv run pre-commit install --hook-type commit-msg`.

IDE/agent integrations may inject `Co-authored-by: Cursor <cursoragent@cursor.com>`
automatically. Inspect the final message with `git log -1 --pretty=format:%B`
before push even when hooks are installed.

## Template reuse

Human docs: `docs/template-onboarding.md`, `docs/template-usage.md`,
`TEMPLATE_FREEZE_CHECKLIST.md`.

Agent workflow: `.ai-rules/template-onboarding.md` + `.commands/template-onboard.md`.

## Updating this stack

- New **binding** rule → `.ai-rules/<topic>.md` + index lines in `AGENTS.md` /
  `CLAUDE.md` / `.cursor/rules/project.mdc`
- New **workflow** → `.ai-rules/` + mention in `docs/ai-workflows.md`
- New **persona** → `agents/` + row in this file
- New **command prompt** → `.commands/` + row in this file
- Extend `scripts/validate-ai-workflows.sh` when adding required paths

Mechanical enforcement: `docs/ci-policy-guards.md`.
