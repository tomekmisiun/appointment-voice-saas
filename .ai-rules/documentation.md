# Documentation Rules

`.ai-rules/` governs agent behavior. User-facing documentation lives in
`README.md`, `docs/`, and project tracking files.

## Accuracy

- MUST NOT invent features, endpoints, or completed work.
- Document only behavior that exists in code and tests.
- Before documenting endpoints, verify routes in code or OpenAPI output.

## README

Update `README.md` when a change affects:

- setup, Docker, environment variables, migrations, tests, or workflows
- API overview, auth flow, roles, permissions, or rate limiting
- known production gaps

Do not update `README.md` for refactors that do not change behavior, setup, API,
configuration, migrations, or workflows.

## Docs Directory

- Auth, deploy, migration, worker, tenancy, or observability changes MUST
  update the matching file under `docs/` when one exists. See the table in
  `docs/template-onboarding.md`.

## Project Tracking Files

- `PROJECT_STATUS.md`: verified implemented capabilities only. MUST NOT mark
  planned work as complete.
- **`docs/CURRENT_STATE.md`**: code-verified implementation snapshot. **MUST**
  update in the same change set when marking a roadmap item complete, when
  changing verified rows in `PROJECT_STATUS.md`, or when adding/removing product
  routes, models, migrations, or their primary tests.
- `TECH_DEBT.md`: when closing an item, update its Status to Done in the same
  change set.
- `ROADMAP.md`: planned work and priorities only.
- README known gaps MUST stay aligned with closed ROADMAP tiers (P0–P2) and
  optional P3 / open `TECH_DEBT.md` items. MUST NOT claim production-ready while
  Critical or High debt remains open in `TECH_DEBT.md`.

## AI Rules And Workflows

- Binding rules: `.ai-rules/` (see `AGENTS.md`, `docs/ai-workflows.md`).
- Optional personas: `agents/`; optional prompts: `.commands/`.
- Feature specs: `docs/specs/`; ADRs: `docs/adr/` (see `docs/decisions/README.md`).
- After changing workflow files, run `make validate-ai-workflows`.

## Enforcement vs Policy

- Mechanical checks live in CI, pre-commit, and `docs/ci-policy-guards.md`.
- `.ai-rules/` keeps judgment rules that automation cannot enforce.

## Writing Style

- Keep wording clear, technical, and concise.
- Avoid hype, marketing language, excessive badges, and emojis.
- Prefer commands and examples that match the repository.
