#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"
# shellcheck source=scripts/ci/lib_ai_commit_trailers.sh
source "$ROOT/scripts/ci/lib_ai_commit_trailers.sh"

usage() {
  cat <<'EOF'
Usage:
  check_no_ai_commit_trailers.sh                 Check commits in CI/local diff range
  check_no_ai_commit_trailers.sh --commit SHA   Check one commit message
  check_no_ai_commit_trailers.sh --message-file F Check a proposed commit message file
EOF
}

check_commit_sha() {
  local sha="$1"
  local msg_file
  msg_file="$(mktemp)"

  git log -1 --format=%B "$sha" >"$msg_file"
  if ! message_has_ai_commit_trailers "$msg_file"; then
    rm -f "$msg_file"
    printf 'Commit: %s\n' "$sha" >&2
    git log -1 --oneline "$sha" >&2
    return 1
  fi
  rm -f "$msg_file"
}

check_commit_range() {
  local base_ref="$1"
  local sha errors=0

  if ! git rev-parse "$base_ref" >/dev/null 2>&1; then
    echo "ai-commit-trailers: base ref not found: $base_ref" >&2
    return 1
  fi

  mapfile -t commits < <(git rev-list "${base_ref}..HEAD" || true)
  if [ "${#commits[@]}" -eq 0 ]; then
    echo "ai-commit-trailers: ok (no commits in ${base_ref}..HEAD)"
    return 0
  fi

  for sha in "${commits[@]}"; do
    if ! check_commit_sha "$sha"; then
      errors=1
    fi
  done

  if [ "$errors" -ne 0 ]; then
    cat <<EOF >&2

Fix every commit in the range before push/merge.
Agents must show the exact commit message and verify it contains no AI trailers.
EOF
    return 1
  fi

  echo "ai-commit-trailers: ok (${#commits[@]} commit(s) in ${base_ref}..HEAD)"
}

case "${1:-}" in
  --help|-h)
    usage
    exit 0
    ;;
  --message-file)
    msg_file="${2:?message file required}"
    message_has_ai_commit_trailers "$msg_file"
    echo "ai-commit-trailers: ok (message file)"
    ;;
  --commit)
    check_commit_sha "${2:?commit SHA required}"
    echo "ai-commit-trailers: ok (commit ${2})"
    ;;
  "")
    base_ref="$(resolve_base_ref)"
    check_commit_range "$base_ref"
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
