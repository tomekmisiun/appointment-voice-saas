#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"

OVERRIDE="scripts/ci/allow-migration-drops"

mapfile -t added_migrations < <(added_files | grep -E '^alembic/versions/.*\.py$' || true)

if [ "${#added_migrations[@]}" -eq 0 ]; then
  echo "migration-drops: no new migrations"
  exit 0
fi

allow_drops=false
if [ "${CI_ALLOW_MIGRATION_DROPS:-}" = "1" ]; then
  allow_drops=true
elif override_file_updated "$OVERRIDE" && override_file_has_reason "$OVERRIDE"; then
  allow_drops=true
fi

patterns=(
  'op\.drop_column'
  'op\.drop_table'
  'op\.drop_index'
  'op\.execute\("DROP'
  "op\.execute\\('DROP"
)

violations=()
for migration in "${added_migrations[@]}"; do
  for pattern in "${patterns[@]}"; do
    if grep -Eq "$pattern" "$ROOT/$migration"; then
      violations+=("$migration:$pattern")
    fi
  done
done

if [ "${#violations[@]}" -eq 0 ]; then
  echo "migration-drops: ok"
  exit 0
fi

if [ "$allow_drops" = true ]; then
  echo "migration-drops: destructive operations allowed via override"
  printf '  %s\n' "${violations[@]}"
  exit 0
fi

cat <<EOF
ERROR: New migration(s) contain destructive Alembic operations:

EOF
printf '  %s\n' "${violations[@]}"
cat <<EOF

Use expand/contract across releases, or document an approved breaking migration
by updating scripts/ci/allow-migration-drops with a one-line reason.

See docs/ci-policy-guards.md and docs/migration-rollback.md
EOF
exit 1
