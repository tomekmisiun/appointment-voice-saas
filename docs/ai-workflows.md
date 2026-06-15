# AI Workflows

How AI tooling should use this repository's rules, personas, and commands.

## Layers

| Layer | Location | Binding? | Purpose |
|-------|----------|----------|---------|
| **Project rules** | `.ai-rules/` | **Yes** | Architecture, security, testing, git, docs, anti-overengineering — must follow |
| **Codex entry index** | `AGENTS.md` | Pointer only | Codex CLI entry; points to `.ai-rules/` |
| **Claude Code entry index** | `CLAUDE.md` | Pointer only | Claude Code CLI entry; points to `.ai-rules/` |
| **Cursor wrappers** | `.cursor/rules/*.mdc` | Pointer only | Cursor entry; points to `.ai-rules/` and must not duplicate rule bodies |
| **Workflow rules** | `.ai-rules/agent-orchestration.md`, `learning-mode.md`, etc. | **Yes** | How to start tasks, plan, review, explain changes |
| **Model routing** | `.ai-rules/model-routing.md` | **Yes** | Model/tier selection and cross-provider review decision tree |
| **Cross-provider review** | `scripts/ai/invoke-cross-reviewer.sh` | Tooling | Read-only opposite-provider Reviewer invocation |
| **Personas** | `agents/` | Optional | Review lenses (backend, security, tenancy, …) |
| **Commands** | `.commands/` | Optional | Prompt formats and procedures for spec/plan/review/onboard |
| **Specs** | `docs/specs/` | Optional | Larger feature specs before implementation |
| **ADRs** | `docs/adr/` | Reference | Recorded architecture decisions |

## Start every task

1. Read `.ai-rules/agent-orchestration.md`
2. Check `.ai-rules/model-routing.md` for model/tier selection and the
   cross-provider review decision tree
3. Use `.ai-rules/context-map.md` to open relevant binding rules and code paths
4. Always include `.ai-rules/anti-overengineering.md` before adding files,
   dependencies, abstractions, or large rewrites.
5. For non-trivial work: `.ai-rules/spec-driven-development.md` →
   `.ai-rules/planning-and-task-breakdown.md` → `.ai-rules/incremental-work.md`
6. Before merge: `.ai-rules/review.md`
7. Learning the repo or mentor-style explanations: `docs/learning/` +
   `.ai-rules/learning-mode.md`

## Tool Entry Points

| Tool | Entry point | Anti-overengineering source |
|------|-------------|-----------------------------|
| Cursor | `.cursor/rules/project.mdc` | `.ai-rules/anti-overengineering.md` |
| Codex CLI | `AGENTS.md` | `.ai-rules/anti-overengineering.md` |
| Claude Code CLI | `CLAUDE.md` | `.ai-rules/anti-overengineering.md` |

## Two-agent review (Builder + Reviewer)

For non-trivial file-changing tasks, the active Builder Agent completes the
work, runs applicable validation, then automatically invokes a read-only
Reviewer before the final response — preferring **cross-provider review**,
with a native same-provider read-only Reviewer fallback.

1. The user gives one normal task.
2. Builder follows the relevant `.ai-rules/`, edits the workspace if needed,
   and runs validation.
3. Builder first tries `scripts/ai/invoke-cross-reviewer.sh <opposite-provider>`
   (see `.ai-rules/model-routing.md` §7); if unavailable or it exits non-zero,
   Builder invokes the same-provider read-only Reviewer path.
4. Reviewer stays read-only and inspects current git diff, untracked files,
   validation output, security and production risks, tests, docs drift,
   overengineering, and scope creep.
5. Builder waits for the Reviewer result.
6. Builder returns a combined final response with Builder summary and Reviewer
   verdict, without applying any fixes automatically.
7. The user can say `fix` to request fixes or `approve` to allow
   commit/push/merge/delete operations under `.ai-rules/git.md`.

Codex CLI reaches this through `AGENTS.md`: try
`scripts/ai/invoke-cross-reviewer.sh claude`, then fall back to native
same-provider `codex review --uncommitted` via
`scripts/ai/invoke-cross-reviewer.sh codex`. Claude Code reaches it through
`CLAUDE.md`: try `scripts/ai/invoke-cross-reviewer.sh codex`, then fall back to
the native `code-reviewer` subagent in `.claude/agents/code-reviewer.md`.
Cursor reaches the binding rule through `.cursor/rules/project.mdc` and follows
the same model-routing policy (`.ai-rules/model-routing.md`); if neither
cross-provider nor native same-provider review is available in the active
Cursor environment, it must produce a `.commands/builder-handoff.md` handoff
and tell the user how to run cross-provider review manually.

`.commands/builder-handoff.md` is the concise Builder handoff format (no pasted
diff). Claude Reviewer reads **only** `.ai-rules/review-checklist.md`; native
Codex `review --uncommitted` cannot receive a custom checklist prompt together
with its scoped review flag in Codex CLI 0.139.0. Not a manual copy-paste
requirement for Codex CLI or Claude Code.

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
| Two-agent review (Reviewer) | `.ai-rules/review-checklist.md` |
| Security audit | `.commands/security-audit.md` |
| Clone for new product | `.commands/template-onboard.md` |
| Sync tracking docs | `.commands/update-project-status.md` |
| Learn the codebase | `docs/learning/00-current-state-audit.md` |

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
