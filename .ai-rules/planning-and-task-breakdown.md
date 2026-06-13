# Planning and Task Breakdown

Break non-trivial work into **small, verifiable tasks**. One task should fit one
focused PR when possible.

## Task card format

Each task MUST include:

| Field | Content |
|-------|---------|
| **Title** | Imperative, specific (`Add keyset cursor validation test`) |
| **Scope** | What changes; what is excluded |
| **Acceptance criteria** | Tests, behavior, docs that prove done |
| **Likely files** | Paths under `app/`, `tests/`, `alembic/`, `docs/` |
| **Validation** | e.g. `pytest tests/test_users.py -q`, then `make validate` |
| **Dependencies** | Prior tasks, migrations, env flags |
| **Rollback / safety** | Migration downgrade, feature flag, deploy note (if relevant) |

## Ordering

1. Schema / migration (if needed) before services that depend on it
2. Service logic before route wiring
3. Tests with or immediately after each slice
4. Docs and tracking files (`PROJECT_STATUS.md`, `ROADMAP.md`, `TECH_DEBT.md`)
   in the **same PR** as the code they describe

## Roadmap and tech debt

- Pick the next item from `ROADMAP.md` in priority order unless the user
  specifies otherwise.
- Map debt IDs from the roadmap row to `TECH_DEBT.md`; mark **Done** only after
  verification.
- Do not batch unrelated roadmap numbers in one PR.

## Estimation hint

| Size | Guideline |
|------|-----------|
| S | One file, one test file, no migration |
| M | Several files, one migration, docs touch |
| L | Cross-cutting; split into multiple task cards |

Use `.commands/plan.md` to generate task cards from a spec or roadmap item.
