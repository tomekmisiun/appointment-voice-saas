# Spec-Driven Development

Use for **non-trivial** features, roadmap items, or multi-file changes. Skip for
one-line fixes, typos, and pure doc index updates.

## When required

- New API surface, model, migration, worker job type, or security boundary
- ROADMAP / TECH_DEBT items marked Medium effort or higher
- Any change the user describes as a "feature" or "epic"

## Spec template

Write the spec in the task (chat/PR) or in `docs/specs/<slug>.md` for large
work. Include:

1. **Objective** — one sentence outcome.
2. **Problem / user story** — who needs what and why.
3. **Requirements** — numbered, testable statements.
4. **Non-goals** — what this change explicitly does not do.
5. **Acceptance criteria** — observable pass/fail checks (prefer tests).
6. **Impacted files** — routes, services, models, migrations, docs, CI.
7. **Risks** — security, tenancy, migrations, performance, deploy.
8. **Verification plan** — commands (`make validate`, targeted pytest paths).
9. **Open questions** — only if truly blocking; max one batch of questions.

## Rules

- MUST align with `.ai-rules/architecture.md` (thin routes, services own logic).
- MUST NOT mark ROADMAP/TECH_DEBT/PROJECT_STATUS items Done without code + tests.
- Prefer **one PR per roadmap task** when using `.commands/build-next-roadmap-task.md`.
- Breaking API changes MUST be called out and documented in README/API sections.

## Handoff to implementation

After the spec is agreed (or implied by a clear user request):

1. Break into tasks — `.ai-rules/planning-and-task-breakdown.md`
2. Implement in slices — `.ai-rules/incremental-work.md`
3. Review before merge — `.ai-rules/review.md`

See `docs/specs/README.md` for repo spec conventions.
