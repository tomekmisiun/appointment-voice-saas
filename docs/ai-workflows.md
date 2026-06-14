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
| **Commands** | `.commands/` | Optional | Prompt formats and procedures for spec/plan/review/onboard |
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

For non-trivial file-changing tasks, the active Builder Agent completes the
work, runs applicable validation, then automatically invokes the native
read-only Reviewer subagent before the final response.

1. The user gives one normal task.
2. Builder follows the relevant `.ai-rules/`, edits the workspace if needed,
   and runs validation.
3. Builder invokes the Reviewer subagent automatically.
4. Reviewer stays read-only and inspects current git diff, untracked files,
   validation output, security and production risks, tests, docs drift,
   overengineering, and scope creep.
5. Builder waits for the Reviewer result.
6. Builder returns a combined final response with Builder summary and Reviewer
   verdict.
7. The user can say `fix` to request fixes or `approve` to allow
   commit/push/merge/delete operations under `.ai-rules/git.md`.

Codex CLI reaches this through `AGENTS.md` and the native `reviewer` subagent in
`.codex/agents/reviewer.toml`. Claude Code reaches it through `CLAUDE.md` and
the native `code-reviewer` subagent in `.claude/agents/code-reviewer.md`.
Cursor reaches the binding rule through `.cursor/rules/project.mdc`; if native
subagent review is not available in the active Cursor environment, it must still
follow `.ai-rules/agent-orchestration.md`.

`.commands/builder-handoff.md` remains the structured Builder handoff format.
`.commands/two-agent-review.md` remains the Reviewer procedure. They are not a
manual copy-paste requirement for Codex CLI or Claude Code.

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
| Two-agent handoff (Builder) | `.commands/builder-handoff.md` |
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
