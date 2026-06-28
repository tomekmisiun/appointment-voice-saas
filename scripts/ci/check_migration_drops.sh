#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"

OVERRIDE="scripts/ci/allow-migration-drops"

# Only scan upgrade() — downgrade() rollbacks are expected to use op.drop_*.
migration_upgrade_body() {
  awk '/^def upgrade\(/ {found=1; next} /^def downgrade\(/ {found=0} found' "$1"
}

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
  upgrade_body="$(migration_upgrade_body "$ROOT/$migration")"
  if [ -z "$upgrade_body" ]; then
    echo "migration-drops: warning: no upgrade() body in $migration" >&2
    continue
  fi
  for pattern in "${patterns[@]}"; do
    if printf '%s\n' "$upgrade_body" | grep -Eq "$pattern"; then
      violations+=("$migration:upgrade():$pattern")
    fi
  done
done

if [ "${#violations[@]}" -eq 0 ]; then
  echo "migration-drops: ok (upgrade() only; downgrade() drops ignored)"
  exit 0
fi

if [ "$allow_drops" = true ]; then
  echo "migration-drops: destructive upgrade() operations allowed via override"
  printf '  %s\n' "${violations[@]}"
  exit 0
fi

cat <<EOF
ERROR: New migration(s) contain destructive Alembic operations in upgrade():

EOF
printf '  %s\n' "${violations[@]}"
cat <<EOF

Use expand/contract across releases, or document an approved breaking migration
by updating scripts/ci/allow-migration-drops with a one-line reason.

See docs/development/ci-policy.md and docs/operations/runbooks/migration-rollback.md
EOF
exit 1
