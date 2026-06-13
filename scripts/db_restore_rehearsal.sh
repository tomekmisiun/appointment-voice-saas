#!/usr/bin/env bash
set -euo pipefail

BACKUP_MODE="${BACKUP_MODE:-local-docker}"
BACKUP_FILE="${BACKUP_FILE:-backups/app_db.dump}"
DB_NAME="${DB_NAME:-app_db}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-app_user}"
RESTORE_CHECK_DB="${RESTORE_CHECK_DB:-app_restore_check}"
DRY_RUN="${DRY_RUN:-false}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

verification_sql="$(ROOT_DIR="${PWD}" python3 - <<'PY'
from app.ops.restore_verification import build_restore_verification_sql

print(build_restore_verification_sql())
PY
)"

echo "Restore rehearsal mode: ${BACKUP_MODE}"
echo "Backup file: ${BACKUP_FILE}"
echo "Temporary restore database: ${RESTORE_CHECK_DB}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "Dry run enabled. Would restore ${BACKUP_FILE} into ${RESTORE_CHECK_DB} and run verification SQL."
  exit 0
fi

run_restore_local_docker() {
  docker compose exec -T "${DB_SERVICE}" dropdb -U "${DB_USER}" --if-exists "${RESTORE_CHECK_DB}"
  docker compose exec -T "${DB_SERVICE}" createdb -U "${DB_USER}" "${RESTORE_CHECK_DB}"
  docker compose exec -T "${DB_SERVICE}" pg_restore -U "${DB_USER}" -d "${RESTORE_CHECK_DB}" < "${BACKUP_FILE}"
  printf '%s\n' "${verification_sql}" | docker compose exec -T "${DB_SERVICE}" psql -U "${DB_USER}" -d "${RESTORE_CHECK_DB}" -v ON_ERROR_STOP=1
  docker compose exec -T "${DB_SERVICE}" dropdb -U "${DB_USER}" --if-exists "${RESTORE_CHECK_DB}"
}

run_restore_direct() {
  if [[ -n "${RESTORE_ADMIN_DATABASE_URL:-}" ]]; then
    admin_db_url="${RESTORE_ADMIN_DATABASE_URL}"
  elif [[ -n "${DATABASE_URL:-}" ]]; then
    admin_db_url="${DATABASE_URL%/*}/postgres"
  else
    echo "RESTORE_ADMIN_DATABASE_URL or DATABASE_URL is required for direct restore mode." >&2
    exit 1
  fi

  restore_db_url="${admin_db_url%/*}/${RESTORE_CHECK_DB}"

  psql "${admin_db_url}" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"${RESTORE_CHECK_DB}\";"
  psql "${admin_db_url}" -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${RESTORE_CHECK_DB}\";"
  pg_restore --dbname="${restore_db_url}" "${BACKUP_FILE}"
  printf '%s\n' "${verification_sql}" | psql "${restore_db_url}" -v ON_ERROR_STOP=1
  psql "${admin_db_url}" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS \"${RESTORE_CHECK_DB}\";"
}

case "${BACKUP_MODE}" in
  local-docker)
    run_restore_local_docker
    ;;
  direct)
    run_restore_direct
    ;;
  *)
    echo "BACKUP_MODE must be one of: local-docker, direct." >&2
    exit 1
    ;;
esac

echo "Restore rehearsal completed successfully."
