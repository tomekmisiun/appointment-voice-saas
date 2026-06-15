#!/usr/bin/env bash
# Invoke a read-only advisory Reviewer for the current uncommitted diff.
#
# Usage:
#   scripts/ai/invoke-cross-reviewer.sh <claude|codex> [handoff-file]
#
# The invoked CLI is run read-only (claude: --permission-mode plan, codex:
# global -s read-only -a never).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PROVIDER="${1:-}"
HANDOFF_FILE="${2:-}"

usage() {
  cat >&2 <<'EOF'
Usage: scripts/ai/invoke-cross-reviewer.sh <claude|codex> [handoff-file]

Runs a read-only advisory review of the current diff:
  - claude : invokes the Claude Code CLI (claude -p --permission-mode plan)
  - codex  : invokes native Codex review (global -s read-only -a never,
             review --uncommitted)

[handoff-file] is an optional path to a filled-in Builder handoff
(.commands/builder-handoff.md format). Claude receives git status/diff because
it has no native uncommitted-review mode; Codex uses native --uncommitted and
does not accept a custom prompt with scoped review flags in CLI 0.139.0.

On failure, fall back according to .ai-rules/agent-orchestration.md.
EOF
}

if [[ "$PROVIDER" != "claude" && "$PROVIDER" != "codex" ]]; then
  usage
  exit 2
fi

REQUIRED_FILES=(
  ".ai-rules/review-checklist.md"
  ".commands/builder-handoff.md"
)
for f in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "$ROOT/$f" ]]; then
    echo "invoke-cross-reviewer: missing required file: $f" >&2
    exit 1
  fi
done

if [[ -n "$HANDOFF_FILE" && ! -f "$HANDOFF_FILE" ]]; then
  echo "invoke-cross-reviewer: handoff file not found: $HANDOFF_FILE" >&2
  exit 1
fi

if ! command -v "$PROVIDER" >/dev/null 2>&1; then
  echo "invoke-cross-reviewer: '$PROVIDER' CLI not found on PATH." >&2
  echo "invoke-cross-reviewer: fall back according to" \
       ".ai-rules/agent-orchestration.md." >&2
  exit 1
fi

# Concrete model selection (see .ai-rules/model-routing.md #9). Resolution
# order: AI_REVIEW_MODEL (absolute override) > provider-specific
# *_REVIEW_MODEL > hardcoded tier default (this table) > CLI default.
AI_REVIEW_TIER="${AI_REVIEW_TIER:-strong_reviewer}"

# Hardcoded default reviewer model per provider+tier. This table is the
# source of truth for reviewer model defaults; edit it here to change
# defaults (see .ai-rules/model-routing.md #9).
default_model_for_tier() {
  local provider="$1"
  local tier="$2"

  case "$provider:$tier" in
    claude:cheap_fast) echo "claude-haiku-4-5" ;;
    claude:standard_builder) echo "claude-sonnet-4-6" ;;
    claude:strong_builder) echo "claude-sonnet-4-6" ;;
    claude:strong_reviewer) echo "claude-opus-4-8" ;;
    claude:max_risk_review) echo "claude-opus-4-8" ;;

    codex:cheap_fast) echo "gpt-5.4-mini" ;;
    codex:standard_builder) echo "gpt-5.4" ;;
    codex:strong_builder) echo "gpt-5.5" ;;
    codex:strong_reviewer) echo "gpt-5.5" ;;
    codex:max_risk_review) echo "gpt-5.5" ;;

    *) echo "" ;;
  esac
}

case "$PROVIDER" in
  claude)
    if [[ -n "${AI_REVIEW_MODEL:-}" ]]; then
      REVIEW_MODEL="$AI_REVIEW_MODEL"
      echo "Using AI_REVIEW_MODEL=$REVIEW_MODEL for provider=$PROVIDER." >&2
    elif [[ -n "${CLAUDE_REVIEW_MODEL:-}" ]]; then
      REVIEW_MODEL="$CLAUDE_REVIEW_MODEL"
      echo "Using CLAUDE_REVIEW_MODEL=$REVIEW_MODEL." >&2
    else
      REVIEW_MODEL="$(default_model_for_tier "$PROVIDER" "$AI_REVIEW_TIER")"
      if [[ -n "$REVIEW_MODEL" ]]; then
        echo "Using hardcoded model mapping: provider=$PROVIDER tier=$AI_REVIEW_TIER model=$REVIEW_MODEL." >&2
      else
        echo "No concrete model found for provider=$PROVIDER tier=$AI_REVIEW_TIER; using CLI default model." >&2
      fi
    fi
    ;;
  codex)
    if [[ -n "${AI_REVIEW_MODEL:-}" ]]; then
      REVIEW_MODEL="$AI_REVIEW_MODEL"
      echo "Using AI_REVIEW_MODEL=$REVIEW_MODEL for provider=$PROVIDER." >&2
    elif [[ -n "${CODEX_REVIEW_MODEL:-}" ]]; then
      REVIEW_MODEL="$CODEX_REVIEW_MODEL"
      echo "Using CODEX_REVIEW_MODEL=$REVIEW_MODEL." >&2
    else
      REVIEW_MODEL="$(default_model_for_tier "$PROVIDER" "$AI_REVIEW_TIER")"
      if [[ -n "$REVIEW_MODEL" ]]; then
        echo "Using hardcoded model mapping: provider=$PROVIDER tier=$AI_REVIEW_TIER model=$REVIEW_MODEL." >&2
      else
        echo "No concrete model found for provider=$PROVIDER tier=$AI_REVIEW_TIER; using CLI default model." >&2
      fi
    fi
    ;;
esac

build_claude_prompt() {
  echo "# Cross-provider read-only review request"
  echo
  echo "You are an external, read-only Reviewer for this repository, invoked"
  echo "from a different AI provider/CLI than the Builder that made these"
  echo "changes."
  echo
  echo "## Hard rules"
  echo "- Review only. Do NOT edit, create, move, or delete any files."
  echo "- Do NOT run destructive or mutating commands: no git commit, push,"
  echo "  merge, checkout, reset, clean, rm, branch deletion, or package"
  echo "  installs."
  echo "- Diff-first review: start from the 'git status' / diff output below."
  echo "  Read only the files the diff touches, plus directly related tests"
  echo "  when needed."
  echo "- Do not scan the whole repository unless the diff requires it."
  echo "- Load at most one specialized persona from agents/, and only if the"
  echo "  diff is narrow and clearly domain-specific."
  echo "- Output MUST use exactly the section headings defined in the"
  echo "  'Output format (required sections)' section of"
  echo "  .ai-rules/review-checklist.md below."
  echo
  echo "## Review context"
  echo "- AI_REVIEW_TIER: $AI_REVIEW_TIER (see .ai-rules/model-routing.md #9;"
  echo "  selects the default reviewer model via the hardcoded tier table"
  echo "  unless overridden by AI_REVIEW_MODEL/CLAUDE_REVIEW_MODEL/CODEX_REVIEW_MODEL)"
  echo "- Reviewer model: ${REVIEW_MODEL:-<CLI default model>}"
  echo

  echo "## Review checklist (.ai-rules/review-checklist.md)"
  echo '```markdown'
  cat "$ROOT/.ai-rules/review-checklist.md"
  echo '```'
  echo
  echo "## Builder handoff format (.commands/builder-handoff.md)"
  echo '```markdown'
  cat "$ROOT/.commands/builder-handoff.md"
  echo '```'
  echo

  if [[ -n "$HANDOFF_FILE" ]]; then
    echo "## Builder handoff (filled in)"
    echo '```markdown'
    cat "$HANDOFF_FILE"
    echo '```'
    echo
  fi

  echo "## git status --short"; echo '```'; git status --short; echo '```'; echo
  echo "## git diff --stat"; echo '```'; git diff --stat; echo '```'; echo
  echo "## git diff"; echo '```diff'; git diff; echo '```'; echo
  echo "## git diff --cached"; echo '```diff'; git diff --cached; echo '```'; echo
  echo "## untracked files"; echo '```'; git ls-files --others --exclude-standard; echo '```'; echo

  while IFS= read -r file; do
    if [[ -f "$file" ]]; then
      echo "### untracked: $file"; echo '```'
      sed -n '1,400p' "$file" || true; echo '```'; echo
    fi
  done < <(git ls-files --others --exclude-standard)
}

OUTPUT=""
STATUS=0

case "$PROVIDER" in
  claude)
    if ! claude -p --help >/dev/null 2>&1; then
      echo "invoke-cross-reviewer: 'claude -p' (non-interactive print mode)" \
           "is not available with this Claude Code CLI." >&2
      echo "invoke-cross-reviewer: fall back to .claude/agents/code-reviewer.md." >&2
      exit 1
    fi
    MODEL_ARGS=()
    if [[ -n "$REVIEW_MODEL" ]]; then
      MODEL_ARGS=(--model "$REVIEW_MODEL")
    fi
    PROMPT_FILE="$(mktemp)"
    trap 'rm -f "$PROMPT_FILE"' EXIT
    build_claude_prompt > "$PROMPT_FILE"
    set +e
    OUTPUT="$(claude -p --permission-mode plan --output-format text \
      "${MODEL_ARGS[@]}" < "$PROMPT_FILE")"
    STATUS=$?
    set -e
    ;;
  codex)
    if ! codex review --help >/dev/null 2>&1; then
      echo "invoke-cross-reviewer: 'codex review' (native review mode) is not" \
           "available with this Codex CLI." >&2
      exit 1
    fi
    CODEX_GLOBAL_ARGS=(-s read-only -a never)
    if [[ -n "$REVIEW_MODEL" ]]; then
      CODEX_GLOBAL_ARGS+=(-m "$REVIEW_MODEL")
    fi
    set +e
    OUTPUT="$(codex "${CODEX_GLOBAL_ARGS[@]}" review --uncommitted)"
    STATUS=$?
    set -e
    ;;
esac

if [[ "$STATUS" -ne 0 ]]; then
  echo "invoke-cross-reviewer: '$PROVIDER' invocation failed (exit $STATUS)." >&2
  echo "invoke-cross-reviewer: fall back according to" \
       ".ai-rules/agent-orchestration.md." >&2
  exit 1
fi

printf '%s\n' "$OUTPUT"

if [[ "$PROVIDER" == "claude" ]]; then
  REQUIRED_HEADINGS=(
    "## Blockers"
    "## Should-fix"
    "## Nice-to-have"
    "## Validation concerns"
    "## Security/production risks"
    "## Overengineering/scope creep"
    "## Final verdict"
  )

  missing=0
  for heading in "${REQUIRED_HEADINGS[@]}"; do
    if ! grep -qF "$heading" <<<"$OUTPUT"; then
      echo "invoke-cross-reviewer: WARNING: '$PROVIDER' output is missing required section: $heading" >&2
      missing=1
    fi
  done

  if [[ "$missing" -ne 0 ]]; then
    echo "invoke-cross-reviewer: output did not match the required Reviewer" \
         "format -- treat as incomplete and consider the same-provider" \
         "Reviewer fallback as well." >&2
    exit 1
  fi
fi
