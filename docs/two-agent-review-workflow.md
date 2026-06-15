# Two-Agent Review Workflow

Lightweight pattern for AI-assisted development: one agent **builds**, a second
read-only Reviewer **reviews** before the Builder gives the final response.
Humans still decide whether to approve commits, pushes, merges, and branch
deletion.

## When to use it

Use for non-trivial file-changing work (features, security, migrations, tenancy,
multi-file refactors). Skip only for read-only work or trivial changes the
author can self-review, and state the skip reason explicitly.

## Roles

### Builder Agent

**Responsibilities:**

- Implement the scoped change on a feature branch (not `main` unless explicitly
  requested).
- Follow `.ai-rules/agent-orchestration.md` and binding rules in `.ai-rules/`.
- Run validation before handoff (`make validate` for app changes; add
  `make policy-guards` when CI, scripts, or AI workflow files change).
- Prepare the **review handoff** using the canonical format:
  **`.commands/builder-handoff.md`** when structured context is needed.
- Automatically invoke the configured Reviewer before the final
  response.
- Include the Builder summary and Reviewer verdict in the final response.
- Do **not** open or merge the PR until review feedback is addressed or
  explicitly waived by the user.

**Does not:** commit, push, merge, or delete branches unless the user explicitly
writes `approve`.

### Reviewer Agent

**Responsibilities:**

- Review **first** — read-only by default.
- Read **only** **`.ai-rules/review-checklist.md`** (checklist + procedure +
  output format). Do not load `.commands/two-agent-review.md` or full
  `.ai-rules/`. Load at most one persona from `agents/` when domain-specific.
- Inspect current git diff, untracked files, validation output, and relevant
  repository files.
- Check architecture, tests, security, tenancy, migrations, Docker/CI, and
  docs/status consistency against binding rules.
- Produce the exact sections defined in `.ai-rules/review-checklist.md`.

**Must not** modify code, commit, push, merge, delete branches, or fix while
reviewing. Fix requests go back to the Builder after the user says `fix`.

**Advisory only:** AI review does not replace CI, tests, branch protection, or
human approval. A Reviewer verdict is input for the author and reviewer human;
the merge gate remains green CI + project policy + explicit user decision.

## Review handoff (Builder → Reviewer)

1. **Builder Agent** — prepare context using **`.commands/builder-handoff.md`**
   when structured handoff context is useful.
2. **Reviewer Agent** — the active tool first tries **cross-provider review**,
   then falls back to its native same-provider read-only Reviewer path:
   - Codex CLI (Builder = Codex): try
     `scripts/ai/invoke-cross-reviewer.sh claude [handoff-file]`; if Claude is
     unavailable or the script exits non-zero, fall back to native
     `codex review --uncommitted` via
     `scripts/ai/invoke-cross-reviewer.sh codex [handoff-file]`.
   - Claude Code (Builder = Claude): try
     `scripts/ai/invoke-cross-reviewer.sh codex [handoff-file]`; if Codex is
     unavailable or the script exits non-zero, fall back to
     `.claude/agents/code-reviewer.md`.
3. **Builder Agent** — waits for the Reviewer result and includes the verdict in
   the final response. The Builder does **not** apply Reviewer feedback
   automatically — feedback is presented to the user, who decides whether to
   request fixes (`fix`) or approve as-is.

## Cross-provider review (Codex ↔ Claude)

`scripts/ai/invoke-cross-reviewer.sh <claude|codex> [handoff-file]` runs the
opposite-provider CLI as an **advisory, read-only** Reviewer over the current
diff:

- **Codex Builder → Claude Reviewer**: from a Codex CLI session,
  `scripts/ai/invoke-cross-reviewer.sh claude` runs
  `claude -p --permission-mode plan` against the current diff,
  `.ai-rules/review-checklist.md`, and `.commands/builder-handoff.md`.
- **Claude Builder → Codex Reviewer**: from a Claude Code session,
  `scripts/ai/invoke-cross-reviewer.sh codex` runs
  native `codex review --uncommitted` with global `-s read-only -a never`.
  Codex CLI 0.139.0 rejects a custom prompt when scoped review flags such as
  `--uncommitted` or `--base` are present, so this path uses the native Codex
  review prompt rather than injecting `.ai-rules/review-checklist.md`.

In both directions:

- The invoked CLI runs in a read-only mode (`--permission-mode plan` for
  Claude, global `-s read-only -a never` for Codex) and must not edit files,
  commit, push, merge, or delete branches.
- The Claude `-p` path checks the output for the required
  `.ai-rules/review-checklist.md` section headings and exits non-zero with a
  warning if any are missing. The native Codex `review --uncommitted` path may
  return CLI-native review formatting because it cannot receive a custom prompt
  together with `--uncommitted` in Codex CLI 0.139.0.
- If the opposite-provider CLI is not installed, or its non-interactive mode
  is unavailable, or the invocation fails, the script exits non-zero with a
  message instructing the Builder to fall back according to
  `.ai-rules/agent-orchestration.md`.
- Reviewer feedback (from either path) is presented to the user; the Builder
  applies fixes only after explicit user approval.

### Verification status (read before relying on this)

- **Verified**: `claude -p --permission-mode plan --output-format text` is the
  Claude CLI non-interactive path used here. `codex review --uncommitted` is
  the native Codex CLI review path; Codex read-only is forced with global
  `-s read-only -a never` before the `review` subcommand.
- **Codex prompt limitation**: although `codex review --help` displays a
  positional `[PROMPT]`, Codex CLI 0.139.0 rejects `[PROMPT]` when
  `--uncommitted`, `--base`, or other scoped review flags are present. The
  native Codex path therefore cannot inject `.ai-rules/review-checklist.md`
  while also using the required uncommitted-change scope.
- **`.codex/agents/reviewer.toml` removed**: Codex CLI 0.139.0 ignored the
  prior TOML role definition as malformed (`unknown field prompt`), so Codex
  review now relies on native `codex review` plus invocation-level sandbox
  flags instead of a role file.
- Large diffs: the Claude `-p` path embeds unstaged diff, staged diff, and
  untracked file contents in the prompt because Claude Code has no local native
  uncommitted-review command equivalent to `codex review --uncommitted`. The
  Codex path uses native `--uncommitted` scope and does not embed a manual diff
  in the prompt.

See `.ai-rules/model-routing.md` §7 for when cross-provider review is
preferred and how model tiers map to Builder/Reviewer roles.

Command bodies live in `.commands/` only — this doc does not duplicate them.
Optional handoff context: spec in `docs/specs/` or a ROADMAP item.

## Reviewer checklist (summary)

Reviewer: **`.ai-rules/review-checklist.md`** (1 page). Humans/Builder:
**`.ai-rules/review.md`**. Load at most one persona when domain-specific:

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

## Reviewer output format

Reviewer output MUST use the sections defined in
`.ai-rules/review-checklist.md`:

- Blockers
- Should-fix
- Nice-to-have
- Validation concerns
- Security/production risks
- Overengineering/scope creep
- Final verdict

Final verdict MUST be one of:

| Verdict | Meaning |
|---------|---------|
| **Approve** | Safe to merge after CI; no material issues |
| **Approve with nits** | Merge acceptable; minor follow-ups optional |
| **Request changes** | Block merge until listed issues are fixed or waived |

## After review

1. Builder addresses **Request changes** items (or user waives them).
2. Re-run validation; update handoff if the diff changed materially.
3. **Review iteration limit:** max **2** reviewer → fix → reviewer cycles per
   task (initial review + one re-review). After the second review, if blockers
   remain, **escalate to the user** — do not auto-loop. User may waive, cut
   scope, or request a manual follow-up.
4. Human opens PR; CI and branch protection must pass.
5. Human merges — agents do not commit, push, merge, force-push, or delete
   branches unless the user explicitly writes `approve`, per
   `.ai-rules/git.md`.

## Related files

| File | Purpose |
|------|---------|
| `.commands/builder-handoff.md` | Concise Builder handoff template |
| `.ai-rules/review-checklist.md` | Reviewer: checklist + procedure + output |
| `.commands/two-agent-review.md` | Human index (points to review-checklist) |
| `.commands/review-current-branch.md` | Single-agent pre-PR review |
| `docs/ai-workflows.md` | Full AI workflow index |
| `.ai-rules/review.md` | Full pre-merge checklist (Builder / humans) |

## What this workflow does not do

- No bots that auto-commit, push, merge, or edit code from review comments.
- No override of CI failures or policy guards.
- No substitute for human judgment on product and deployment decisions.
