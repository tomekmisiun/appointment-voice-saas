# Learning Mode (Mentor Explanations)

Binding for **every non-trivial file-changing task**. Complements
`.ai-rules/agent-orchestration.md` §8 (completion report) and
`.ai-rules/review.md`.

Goal: explain changes like a **backend/DevOps mentor** — precise, beginner-friendly,
grounded in this repo's actual code (not README claims).

## Before changing code

- Read `docs/CURRENT_STATE.md` when unsure what is implemented.
- Use `docs/domain-model.md` to locate entities and their relationships.
- Do not mark features implemented unless verified in code, tests, or migrations.
- When closing a roadmap item (`[x]`) or updating verified status in
  `PROJECT_STATUS.md`, **MUST** refresh `docs/CURRENT_STATE.md`
  in the same change set (see `.ai-rules/documentation.md`).

## Required final response sections

For non-trivial file-changing tasks, the final response MUST include all of:

### Builder summary

One short paragraph: what changed and why (user goal → outcome).

### Reviewer verdict

Verdict from the read-only Reviewer, or `Reviewer skipped: <reason>`.

### Changed files

List every created/modified/deleted file.

### Why each file changed

One line per file — purpose of the edit, not a repeat of the diff.

### What the changed code does

Explain behavior in plain language (what happens at runtime after your change).

### What calls it

Upstream callers: routes, workers, tests, CLI, other services. Name concrete
functions/endpoints.

### What could break

Tenancy, auth, migrations, concurrency, cache, worker jobs, API contract,
backward compatibility — only relevant risks.

### Validation run

Exact commands and PASS/FAIL (e.g. `make validate`, `make policy-guards`).
If skipped, say why.

### Manual verification steps

Concrete steps a human can run (curl, pytest path, migration upgrade, log check).

### Interview-defense explanation

2–5 sentences you could say in a technical interview: problem, approach, trade-off,
how tests/CI prove correctness. No buzzwords without meaning.

## Docs-only tasks

Use the same sections where applicable; omit code-specific subsections if N/A.
Still include validation run and manual verification (e.g. read docs, run
`make validate-ai-workflows`).

## Reference docs

| Doc | Use when |
|-----|----------|
| `docs/CURRENT_STATE.md` | What exists vs planned |
| `docs/domain-model.md` | Product entities and relationships |
| `.ai-rules/context-map.md` | Safe change patterns by task type |
