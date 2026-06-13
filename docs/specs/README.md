# Feature Specs

Optional specs for **non-trivial** features before implementation.

## When to write a spec here

- Multi-file or multi-PR features
- Roadmap items marked M/L effort
- Security-sensitive or tenancy-sensitive changes
- User asks for a spec before coding

Small bug fixes and single-endpoint additions can stay in the PR description or
agent chat only (see `.ai-rules/spec-driven-development.md`).

## File naming

```
docs/specs/<short-kebab-slug>.md
```

Examples: `docs/specs/admin-export-users.md`, `docs/specs/webhook-retry-policy.md`

## Required sections

1. **Objective**
2. **Problem / user story**
3. **Requirements** (numbered, testable)
4. **Non-goals**
5. **Acceptance criteria**
6. **Impacted files**
7. **Risks**
8. **Verification plan** (`make validate`, targeted pytest)
9. **Open questions** (only if blocking)

## Lifecycle

1. Author spec (human or agent via `.commands/spec.md`)
2. Break into tasks (`.commands/plan.md`)
3. Implement incrementally (`.ai-rules/incremental-work.md`)
4. On merge: update `PROJECT_STATUS.md` / `ROADMAP.md` / `TECH_DEBT.md` as needed
   (`.commands/update-project-status.md`)

Specs describe **intent**; `PROJECT_STATUS.md` records **verified** reality after merge.

## Template note

Do not store product-specific business specs in the upstream template unless they
illustrate a pattern. Fork owners add their own specs under `docs/specs/` in the
fork.
