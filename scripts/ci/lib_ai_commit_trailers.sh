#!/usr/bin/env bash
# Shared AI commit-trailer patterns for pre-commit and CI policy guards.
set -euo pipefail

AI_COMMIT_TRAILER_PATTERNS=(
  'cursoragent@cursor\.com'
  '^Co-authored-by:[[:space:]]*Cursor([[:space:]]|<|$)'
  '^Co-authored-by:[[:space:]]*Claude([[:space:]]|<|$)'
  '^Co-authored-by:[[:space:]]*Codex([[:space:]]|<|$)'
  '^Co-authored-by:[[:space:]]*.*(cursor|codex|claude|openai|anthropic|github copilot)'
  '^Authored-by:[[:space:]]*.*(cursor|codex|claude|openai|anthropic|github copilot)'
  '^Generated-by:'
  '^Created-by:[[:space:]]*AI([[:space:]]|$)'
)

ai_commit_trailer_error_message() {
  cat <<'EOF'
ERROR: AI attribution trailers are not allowed in commit messages.

Forbidden examples:
  Co-authored-by: Cursor <cursoragent@cursor.com>
  Co-authored-by: Claude / Codex / OpenAI / Anthropic / GitHub Copilot
  Authored-by: <agent tool>
  Generated-by: ...
  Created-by: AI

Remove all AI co-author and attribution metadata. Human authors only.
See .ai-rules/git.md and docs/development/ci-policy.md
EOF
}

find_ai_commit_trailer_matches() {
  local msg_file="$1"
  local pattern match

  for pattern in "${AI_COMMIT_TRAILER_PATTERNS[@]}"; do
    while IFS= read -r match; do
      [ -n "$match" ] || continue
      printf '%s\n' "$match"
    done < <(grep -Ein "$pattern" "$msg_file" || true)
  done
}

message_has_ai_commit_trailers() {
  local msg_file="$1"
  local matches

  matches="$(find_ai_commit_trailer_matches "$msg_file" | sort -u || true)"
  if [ -n "$matches" ]; then
    ai_commit_trailer_error_message
    printf '\nMatched lines:\n' >&2
    printf '  %s\n' "$matches" >&2
    return 1
  fi

  return 0
}
