# Command: Builder Handoff (Builder Agent)

Use when passing work to the Reviewer. Keep it **short** — Reviewer
runs `git diff` locally; do **not** paste diff or conversation history.

---

**Mode:** structured handoff only. No commit/push/merge unless user writes
`approve`.

## Before handoff

1. Feature branch (not `main` unless requested).
2. Run validation per `.ai-rules/agent-orchestration.md`.
3. Gather: branch name, `git diff --name-status main...HEAD`, validation output.

## Rules

- Do not claim PASS unless the command exited 0 — paste key result lines only.
- State SKIPPED/FAILED clearly.
- Do not paste full `git diff` — Reviewer inspects diff via tools.
- Do not paste chat history — objective + summary only.
- Invoke Reviewer automatically (see `.ai-rules/agent-orchestration.md`).

## Output format (concise)

```markdown
## Builder handoff

**Objective:** <one sentence>

**Branch:** `<name>` (base: `main`)

**Summary:** <2–4 sentences: what changed, key design choice, scope boundary>

**Files changed:**
<paste `git diff --name-status main...HEAD` only>

**Validation:**
| Command | Result | Evidence |
|---------|--------|----------|
| `make validate` | PASS / FAIL / N/A | e.g. "412 passed, cov 85%" |
| `make policy-guards` | PASS / FAIL / N/A | brief |
| `make validate-ai-workflows` | PASS / FAIL / N/A | brief |

**Tests added/changed:** <module paths or "None">

**Migration/API/security/tenant impact:** <one line each, or "None">

**Known risks:** <bullets>

**Reviewer focus:** <bullets — where extra scrutiny helps>
```

After handoff, invoke the configured Reviewer. Reviewer reads
`.ai-rules/review-checklist.md` only.

Reference: `docs/development/workflows/two-agent-review.md`
