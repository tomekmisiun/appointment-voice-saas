# Model Routing Policy

## 1. Purpose

AI tooling in this repository can use multiple models of different cost and
capability. The goal of this policy is to **preserve review quality and
safety while avoiding unnecessary token/cost burn**: cheap, fast models for
mechanical or low-risk work; stronger models reserved for security, data,
tenancy, distributed-systems, and final pre-merge review.

This is **guidance for model/agent selection**, not a binding gate enforced
by CI. `scripts/validate-ai-workflows.sh` only checks that this file exists
and is referenced from `.ai-rules/agent-orchestration.md`; it does not (and
cannot) verify which model was actually used.

## 2. Model tiers

Tiers are defined by capability/cost, not by brand, so the policy applies
across Codex CLI, Claude Code, and Cursor regardless of which specific models
are configured locally.

| Tier | Description |
|------|-------------|
| `cheap_fast` | Smallest/cheapest available model. Good for mechanical edits, formatting, docs wording, simple lookups. |
| `standard_builder` | Default mid-tier model for ordinary implementation work (routes, services, schemas, tests). |
| `strong_builder` | More capable model for high-risk implementation: security, migrations, tenancy, workers, Docker/CI, architecture. |
| `strong_reviewer` | A reviewer model at least as capable as the Builder; used for non-trivial multi-file changes. |
| `max_risk_review` | The strongest available model, reserved for final pre-merge review of high-risk diffs or large architecture refactors. |

## 3. Task classification → recommended tier

| Task | Recommended tier |
|------|-------------------|
| Docs-only typo, README wording, checklist/roadmap update | `cheap_fast` |
| Mechanical rename, small config-only change | `cheap_fast` or `standard_builder` |
| Normal FastAPI route/service/schema/test change | `standard_builder` |
| Multi-file backend feature | `standard_builder` (Builder) + `strong_reviewer` (Reviewer) |
| Auth, authorization, secrets, security headers, OWASP-sensitive changes | `strong_builder` + `strong_reviewer` |
| DB migration, Alembic, SQLAlchemy model, index, transaction, rollback/downgrade | `strong_builder` + `strong_reviewer` |
| Tenancy / tenant isolation / `X-Tenant-Slug` / data separation | `strong_builder` + `strong_reviewer` |
| Workers, Redis, queues, idempotency, retries, distributed locking | `strong_builder` + `strong_reviewer` |
| Docker, CI/CD, production deployment, policy guards | `strong_builder` + `strong_reviewer` |
| Large architecture refactor | `strong_builder` + `max_risk_review` |
| Final pre-merge review of a high-risk diff | `max_risk_review` |

Use `.ai-rules/context-map.md` and `.ai-rules/agent-orchestration.md` §1 (task
classification table) to determine which row applies — this table reuses that
same taxonomy.

## 4. Provider examples (non-binding)

These are illustrative only. **Actual model names must be selected through
local CLI/account configuration** (e.g. Claude Code's `--model`/`/model` or
`model:` subagent frontmatter, Codex CLI's `-m`/`--model` or `-c model=...`,
Cursor's model picker). Do not hardcode a specific model name into binding
rules — model lineups change over time and availability depends on the user's
plan.

- **Claude**: `cheap_fast` examples may include Haiku-class models where
  available; `standard_builder`/`strong_builder` examples may include
  Sonnet-class models; `strong_reviewer`/`max_risk_review` examples may
  include Opus-class models where available.
- **Codex / OpenAI**: cheap/standard/strong tiers should be described
  generically (e.g. "the smaller/faster model available in your Codex
  account" vs. "the most capable reasoning model available") unless the local
  CLI/account exposes specific model names the user has confirmed.
- **Cursor**: use whichever model tiers the user's Cursor plan exposes,
  mapped onto the same `cheap_fast` / `standard_builder` / `strong_builder`
  / `strong_reviewer` / `max_risk_review` tiers.

## 5. Escalation rules

Escalate to at least `strong_builder` (Builder) and `strong_reviewer` or
`max_risk_review` (Reviewer) if the diff touches any of:

- `alembic/versions/` (migrations, schema changes)
- Auth/security files (`app/core/security.py`, auth routes, password reset,
  tokens, sessions)
- Tenancy files (tenant resolution, `X-Tenant-Slug`, tenant-scoped queries)
- Worker/queue/idempotency code (`app/worker.py`, `app/core/job_queue.py`,
  idempotency services)
- Docker/CI/policy guard files (`docker-compose*.yml`, `.github/workflows/`,
  `scripts/ci/`, `Makefile`)
- Migrations, transactions, indexes, constraints
- Rate limiting, secrets, CORS, trusted hosts, production validators
- Production observability and deployment paths (metrics, logging config,
  health checks, deployment manifests, `docs/production-deployment.md`)

When in doubt, escalate one tier rather than under-reviewing a high-risk
change.

## 6. De-escalation rules

It is reasonable to use `cheap_fast` when **all** of the following hold:

- The change is docs-only (no `app/`, `alembic/`, `scripts/`, or config
  changes with production behavior impact).
- No application code is touched.
- The change is small and mechanical (rename, formatting, comment/test-name
  cleanup).
- No security, tenancy, migration, worker, Docker, or CI files are touched.

## 7. Reviewer rule

- The Reviewer should normally be **at least the same tier** as the Builder.
- For high-risk tasks (section 5), the Reviewer should be **stronger** than
  the Builder (`strong_reviewer` or `max_risk_review`).
- **Cross-provider review is preferred** for non-trivial code changes — see
  `scripts/ai/invoke-cross-reviewer.sh` and the decision tree in
  `.ai-rules/agent-orchestration.md` §8. A different provider/model reviewing
  the Builder's work catches blind spots that a same-provider reviewer may
  share.
- If cross-provider review is unavailable, a same-provider read-only Reviewer
  should still be run: Codex uses native `codex review --uncommitted` with
  global `-s read-only -a never`; Claude Code uses the native
  `.claude/agents/code-reviewer.md` subagent.

## 8. Diff-first cost control

To keep review cost proportional to the size of the change, the Reviewer
(same-provider or cross-provider) should:

1. Start with `git status --short`, `git diff --stat`, and `git diff` — not a
   full-repo scan. For native Codex review, `--uncommitted` supplies this
   scope; for Claude `-p`, `scripts/ai/invoke-cross-reviewer.sh` embeds the
   diff in the prompt.
2. Read only the specific files the diff touches, plus targeted lookups for
   call sites/tests when needed.
3. Load **at most one** specialized persona from `agents/` (see
   `.ai-rules/review-checklist.md`), and only when the diff is narrow and
   clearly domain-specific (security, tenancy, DB, Docker/CI).
4. Avoid loading the full `.ai-rules/` tree. Claude `-p` receives
   `.ai-rules/review-checklist.md` in its prompt. Native Codex
   `review --uncommitted` in CLI 0.139.0 does not accept a custom prompt
   together with scoped review flags, so it uses the CLI's native review
   behavior over the uncommitted diff.

## 9. Concrete model selection without extra config files

This file maps **task types to abstract tiers** (section 3). Concrete model
selection happens via a **hardcoded tier→model table inside
`scripts/ai/invoke-cross-reviewer.sh`** (the `default_model_for_tier`
function), plus environment-variable overrides — using only the two existing
files: this policy (`.ai-rules/model-routing.md`) and
`scripts/ai/invoke-cross-reviewer.sh`. No separate local model-mapping file
(e.g. an `.ai-models*.env` file or a `select-model-tier.sh` script) is added.

`AI_REVIEW_TIER` now selects a concrete default reviewer model through this
hardcoded table. **The table in `scripts/ai/invoke-cross-reviewer.sh` is the
source of truth for reviewer model defaults** — edit it there to change
defaults; this section documents the current values but is not itself
authoritative if the two drift.

### Hardcoded tier → model table

| Tier | Claude | Codex |
|------|--------|-------|
| `cheap_fast` | `claude-haiku-4-5` | `gpt-5.4-mini` |
| `standard_builder` | `claude-sonnet-4-6` | `gpt-5.4` |
| `strong_builder` | `claude-sonnet-4-6` | `gpt-5.5` |
| `strong_reviewer` | `claude-opus-4-8` | `gpt-5.5` |
| `max_risk_review` | `claude-opus-4-8` | `gpt-5.5` |

### Cross-provider reviewer model selection (priority order)

`scripts/ai/invoke-cross-reviewer.sh` resolves the concrete reviewer model in
this order:

1. **`AI_REVIEW_MODEL`** — absolute one-off override for the current reviewer
   run, regardless of provider or tier.
2. **Provider-specific override**:
   - `CLAUDE_REVIEW_MODEL` (used when provider is `claude`)
   - `CODEX_REVIEW_MODEL` (used when provider is `codex`)
3. **Hardcoded tier default** — `default_model_for_tier "$PROVIDER"
   "$AI_REVIEW_TIER"` from the table above. `AI_REVIEW_TIER` defaults to
   `strong_reviewer` if unset.
4. **CLI default model** — used only if the hardcoded table returns empty for
   an unrecognized provider/tier combination; the script does not pass a
   `--model`/`-m` flag and the locally configured CLI default is used. This
   should not normally happen for the supported providers/tiers above.

### Examples

```bash
# Absolute override (wins regardless of provider or tier)
AI_REVIEW_MODEL=claude-opus-4-8 scripts/ai/invoke-cross-reviewer.sh claude
AI_REVIEW_MODEL=gpt-5.5 scripts/ai/invoke-cross-reviewer.sh codex

# Provider-specific override (used when AI_REVIEW_MODEL is unset)
CLAUDE_REVIEW_MODEL=claude-opus-4-8 scripts/ai/invoke-cross-reviewer.sh claude
CODEX_REVIEW_MODEL=gpt-5.5 scripts/ai/invoke-cross-reviewer.sh codex

# Tier-driven default (used when no model env var is set)
AI_REVIEW_TIER=max_risk_review scripts/ai/invoke-cross-reviewer.sh claude  # -> claude-opus-4-8
AI_REVIEW_TIER=cheap_fast scripts/ai/invoke-cross-reviewer.sh codex        # -> gpt-5.4-mini
```

- `AI_REVIEW_TIER` names one of the tiers from section 2 (defaults to
  `strong_reviewer` if unset). Claude receives the selected tier/model in the
  prompt; Codex receives the selected model through global `-m` before
  `review --uncommitted`.
- `AI_REVIEW_MODEL`, `CLAUDE_REVIEW_MODEL`, and `CODEX_REVIEW_MODEL` still
  override the hardcoded table, in that priority order.
- Model lineups change over time; when they do, update the
  `default_model_for_tier` table in `scripts/ai/invoke-cross-reviewer.sh` (and
  this table for documentation) — no other file needs to change.

This keeps review token cost roughly proportional to diff size rather than
repository size, regardless of which model tier is used.
