#!/usr/bin/env bash
set -euo pipefail

resolve_base_ref() {
  if [ -n "${CI_BASE_REF:-}" ]; then
    printf '%s\n' "$CI_BASE_REF"
    return
  fi

  if [ "${GITHUB_EVENT_NAME:-}" = "pull_request" ] && [ -n "${GITHUB_BASE_REF:-}" ]; then
    if git rev-parse "origin/${GITHUB_BASE_REF}" >/dev/null 2>&1; then
      printf '%s\n' "origin/${GITHUB_BASE_REF}"
      return
    fi
  fi

  if [ "${GITHUB_EVENT_NAME:-}" = "push" ] && [ -n "${GITHUB_EVENT_BEFORE:-}" ] \
     && [ "${GITHUB_EVENT_BEFORE}" != "0000000000000000000000000000000000000000" ]; then
    printf '%s\n' "${GITHUB_EVENT_BEFORE}"
    return
  fi

  if git rev-parse origin/main >/dev/null 2>&1; then
    printf '%s\n' "origin/main"
    return
  fi

  printf '%s\n' "HEAD~1"
}

changed_files() {
  local base_ref
  base_ref="$(resolve_base_ref)"
  git diff --name-only "${base_ref}...HEAD"
}

added_files() {
  local base_ref
  base_ref="$(resolve_base_ref)"
  git diff --name-only --diff-filter=A "${base_ref}...HEAD"
}

file_changed() {
  local path="$1"
  changed_files | grep -qx "$path"
}

any_path_changed() {
  local pattern="$1"
  changed_files | grep -Eq "$pattern" || return 1
}

any_path_added() {
  local pattern="$1"
  added_files | grep -Eq "$pattern" || return 1
}

override_file_updated() {
  local override_path="$1"
  file_changed "$override_path"
}

override_file_has_reason() {
  local override_path="$1"
  if [ ! -f "$override_path" ]; then
    return 1
  fi
  if [ ! -s "$override_path" ]; then
    return 1
  fi
  grep -Ev '^[[:space:]]*(#|$)' "$override_path" >/dev/null
}
