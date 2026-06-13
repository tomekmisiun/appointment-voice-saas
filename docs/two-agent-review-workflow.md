# Two-Agent Review Workflow

Lightweight pattern for AI-assisted development: one agent **builds**, a second
agent **reviews** before a PR. No automation — humans still merge.

## When to use it

Use for non-trivial branch work (features, security, migrations, tenancy,
multi-file refactors). Skip for one-line fixes the author can self-review.

## Roles

### Builder Agent

**Responsibilities:**

- Implement the scoped change on a feature branch (not `main` unless explicitly
  requested).
- Follow `.ai-rules/agent-orchestration.md` and binding rules in `.ai-rules/`.
- Run validation before handoff (`make validate` for app changes; add
  `make policy-guards` when CI, scripts, or AI workflow files change).
- Output the **review handoff** using the canonical template:
  **`.commands/builder-handoff.md`** (do not improvise a shorter format).
- Do **not** open or merge the PR until review feedback is addressed or
  explicitly waived by the user.

**Does not:** push, merge, delete branches, or commit unless the user asked.

### Reviewer Agent

**Responsibilities:**

- Review **first** — read-only by default.
- Use the canonical prompt: **`.commands/two-agent-review.md`** (in a fresh
  agent session, after the Builder handoff).
- Read `.ai-rules/review.md` and load relevant personas from `agents/`.
- Inspect the handoff: objective, changed files, `git diff main...HEAD`,
  validation output.
- Check architecture, tests, security, tenancy, migrations, Docker/CI, and
  docs/status consistency against binding rules.
- Produce findings in the standard table and a final verdict.

**Must not** modify code, commit, push, merge, or “fix while reviewing” unless
the user explicitly asks the Reviewer Agent to implement fixes.

**Advisory only:** AI review does not replace CI, tests, branch protection, or
human approval. A Reviewer verdict is input for the author and reviewer human;
the merge gate remains green CI + project policy + explicit user decision.

## Review handoff (Builder → Reviewer)

1. **Builder Agent** — run **`.commands/builder-handoff.md`** and paste the
   completed handoff (objective, branch, diff, validation, impact sections).
2. **Reviewer Agent** — open a **new** agent session; paste the handoff, then
   **`.commands/two-agent-review.md`**.

Command bodies live in `.commands/` only — this doc does not duplicate them.
Optional handoff context: spec in `docs/specs/` or a ROADMAP item.

## Reviewer checklist (summary)

Full checklist: `.ai-rules/review.md`. Load personas as needed:

| Area | Persona |
|------|---------|
| Backend / FastAPI | `agents/backend-reviewer.md` |
| Security | `agents/security-auditor.md` |
| Tenancy | `agents/tenancy-reviewer.md` |
| Database / migrations | `agents/database-reviewer.md` |
| Docker / CI | `agents/devops-ci-reviewer.md` |

Also verify:

- Commit messages on the branch have no AI attribution trailers
  (`bash scripts/ci/check_no_ai_commit_trailers.sh`, included in
  `make policy-guards`).
- `PROJECT_STATUS.md`, `ROADMAP.md`, and `TECH_DEBT.md` stay accurate if touched.

## Verdict format

Reviewer output MUST end with one of:

| Verdict | Meaning |
|---------|---------|
| **Approve** | Safe to merge after CI; no material issues |
| **Approve with nits** | Merge acceptable; minor follow-ups optional |
| **Request changes** | Block merge until listed issues are fixed or waived |

Use the output template in `.ai-rules/review.md` (Summary, Findings table,
Validation, Verdict).

## After review

1. Builder addresses **Request changes** items (or user waives them).
2. Re-run validation; update handoff if the diff changed materially.
3. Optional second review pass for large fixes.
4. Human opens PR; CI and branch protection must pass.
5. Human merges — agents do not merge unless explicitly instructed per
   `.ai-rules/git.md`.

## Related files

| File | Purpose |
|------|---------|
| `.commands/builder-handoff.md` | Canonical Builder Agent handoff template |
| `.commands/two-agent-review.md` | Canonical Reviewer Agent prompt |
| `.commands/review-current-branch.md` | Single-agent pre-PR review (same output format) |
| `docs/ai-workflows.md` | Full AI workflow index |
| `.ai-rules/review.md` | Binding pre-merge checklist |

## What this workflow does not do

- No bots that auto-commit, push, merge, or edit code from review comments.
- No override of CI failures or policy guards.
- No substitute for human judgment on product and deployment decisions.
