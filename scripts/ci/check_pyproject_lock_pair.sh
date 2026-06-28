#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"

pyproject_changed=false
lock_changed=false

if any_path_changed '^pyproject\.toml$'; then
  pyproject_changed=true
fi

if any_path_changed '^uv\.lock$'; then
  lock_changed=true
fi

if [ "$pyproject_changed" = false ] && [ "$lock_changed" = false ]; then
  echo "pyproject-lock-pair: no dependency manifest changes"
  exit 0
fi

if [ "$pyproject_changed" = true ] && [ "$lock_changed" = true ]; then
  echo "pyproject-lock-pair: ok"
  exit 0
fi

cat <<EOF
ERROR: pyproject.toml and uv.lock must change together.

Run \`uv lock\` after editing pyproject.toml.

See docs/development/ci-policy.md
EOF
exit 1
