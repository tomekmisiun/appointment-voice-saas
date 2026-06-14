# CLAUDE.md

Binding project rules live in **`.ai-rules/`**. Read the relevant files before
making changes. Do not duplicate rule bodies here.

Workflow overview: **`docs/ai-workflows.md`** · Two-agent review:
**`docs/two-agent-review-workflow.md`**

After every non-trivial file-changing task, Claude Code MUST use the native
`code-reviewer` subagent before the final response. No second user prompt,
pasted handoff, local runner command, or separate CLI window is required. The
final response must include the Builder summary and Reviewer verdict. Read-only
or trivial tasks may skip Reviewer only with an explicit reason.

## Binding rules (`.ai-rules/`)

### Core
- `repository.md` — scope, config hygiene, enforcement split
- `architecture.md` — layers, dependencies
- `api.md` — routes, auth, versioning
- `database.md` — SQLAlchemy, Alembic, destructive migrations
- `security.md` — secrets, auth, production validators
- `tenancy.md` — tenant isolation
- `workers.md` — job queue and Redis compatibility
- `testing.md` — pytest requirements and test integrity
- `docker.md` — Compose and production runtime safety
- `documentation.md` — README, docs, tracking files
- `git.md` — branches, commits (no AI attribution trailers), push/merge approval
- `anti-overengineering.md` — avoid unnecessary abstractions, files, dependencies

### Workflow (how to work)
- `agent-orchestration.md` — start every task here
- `context-map.md` — task type → files to read
- `spec-driven-development.md` — specs for non-trivial work
- `planning-and-task-breakdown.md` — task cards and ordering
- `incremental-work.md` — thin slices and validation cadence
- `tdd-and-regression.md` — failing test first, coverage expectations
- `review.md` — pre-merge checklist
- `learning-mode.md` — mentor-style completion format for non-trivial tasks
- `threat-modeling.md` — auth, tenancy, uploads, webhooks, workers
- `template-onboarding.md` — clone into a new product (agent workflow)

## Optional (not binding)

- **`agents/`** — review personas (backend, security, tenancy, DB, CI, onboarding)
- **`.commands/`** — prompt formats and procedures (spec, plan, builder
  handoff, two-agent review, audit, onboard)
- **`docs/two-agent-review-workflow.md`** — Builder / Reviewer handoff pattern
- **`docs/learning/`** — code-verified mental maps and interview defense
- **`docs/specs/`** — feature spec conventions
- **`docs/decisions/`** → ADRs in **`docs/adr/`**

## Validation

- Application code: `make validate`
- CI policy: `make policy-guards`
- AI workflow files: `make validate-ai-workflows`

Mechanical checks: `docs/ci-policy-guards.md`.

Update `.ai-rules/` when changing project rules. Keep this file as an index only.
