#!/usr/bin/env bash
set -euo pipefail

staged="$(git diff --cached --name-only)"

pyproject_changed=false
lock_changed=false

if grep -qx 'pyproject.toml' <<<"$staged"; then
  pyproject_changed=true
fi

if grep -qx 'uv.lock' <<<"$staged"; then
  lock_changed=true
fi

if [ "$pyproject_changed" = false ] && [ "$lock_changed" = false ]; then
  exit 0
fi

if [ "$pyproject_changed" = true ] && [ "$lock_changed" = true ]; then
  exit 0
fi

cat <<EOF
ERROR: pyproject.toml and uv.lock must be staged together.
Run \`uv lock\` after editing pyproject.toml.
EOF
exit 1
