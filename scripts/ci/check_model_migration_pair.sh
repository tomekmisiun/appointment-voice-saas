#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"

OVERRIDE="$ROOT/scripts/ci/allow-no-migration"

if ! any_path_changed '^app/models/'; then
  echo "model-migration-pair: no model changes detected"
  exit 0
fi

if any_path_added '^alembic/versions/.*\.py$'; then
  echo "model-migration-pair: ok (new migration present)"
  exit 0
fi

if [ "${CI_ALLOW_NO_MIGRATION:-}" = "1" ]; then
  echo "model-migration-pair: bypassed via CI_ALLOW_NO_MIGRATION=1"
  exit 0
fi

if override_file_updated "$OVERRIDE" && override_file_has_reason "$OVERRIDE"; then
  echo "model-migration-pair: bypassed via scripts/ci/allow-no-migration"
  exit 0
fi

cat <<EOF
ERROR: app/models/ changed without a new Alembic revision.

Add a migration under alembic/versions/, or document a non-schema-only model
change by updating scripts/ci/allow-no-migration with a one-line reason.

See docs/ci-policy-guards.md
EOF
exit 1
