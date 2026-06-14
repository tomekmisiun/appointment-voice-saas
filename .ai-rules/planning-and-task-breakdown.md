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

- For Appointment Voice SaaS product tasks, pick the next item from
  `docs/appointment-saas-roadmap.md` (the executable backlog, `AVS-Exxx`
  items) unless the user specifies otherwise. `ROADMAP.md` is the high-level,
  non-executable view.
- Map debt IDs from the roadmap row to `TECH_DEBT.md`; mark **Done** only after
  verification.
- Do not batch unrelated roadmap numbers in one PR.

## Task sizing

- One PR represents one logical change. Tiny, directly related docs/rules
  fixes may be grouped with that change.
- Unrelated changes MUST NOT be bundled into the same PR.
- The following are always separate tasks/PRs — never combine with an
  unrelated roadmap item or with each other:
  - pytest-xdist / test parallelization
  - test database isolation changes
  - migrations
  - auth
  - CI workflow changes
  - Docker / Compose changes
  - booking logic
  - call flow / IVR
  - calendar integration
  - SMS integration
  - security rules (`.ai-rules/security.md`, `app/core/security.py`, etc.)

## Estimation hint

| Size | Guideline |
|------|-----------|
| S | One file, one test file, no migration |
| M | Several files, one migration, docs touch |
| L | Cross-cutting; split into multiple task cards |

Use `.commands/plan.md` to generate task cards from a spec or roadmap item.
