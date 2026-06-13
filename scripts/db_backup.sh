#!/usr/bin/env bash
set -euo pipefail

BACKUP_MODE="${BACKUP_MODE:-local-docker}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
BACKUP_FILE="${BACKUP_FILE:-${BACKUP_DIR}/app_db.dump}"
DB_NAME="${DB_NAME:-app_db}"
DB_SERVICE="${DB_SERVICE:-db}"
DB_USER="${DB_USER:-app_user}"
DRY_RUN="${DRY_RUN:-false}"

mkdir -p "${BACKUP_DIR}"

echo "Backup mode: ${BACKUP_MODE}"
echo "Backup file: ${BACKUP_FILE}"

case "${BACKUP_MODE}" in
  local-docker)
    if [[ "${DRY_RUN}" == "true" ]]; then
      echo "Dry run enabled. Would create a custom-format dump with pg_dump via Docker Compose."
      exit 0
    fi

    docker compose exec -T "${DB_SERVICE}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc > "${BACKUP_FILE}"
    ;;
  direct)
    if [[ -n "${DATABASE_URL:-}" ]]; then
      pg_dump_target="${DATABASE_URL}"
    else
      pg_dump_target="${PGDATABASE:?PGDATABASE or DATABASE_URL is required for direct backup mode}"
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
      echo "Dry run enabled. Would run pg_dump against ${pg_dump_target}."
      exit 0
    fi

    pg_dump -Fc --dbname="${pg_dump_target}" > "${BACKUP_FILE}"
    ;;
  provider-hook)
    : "${BACKUP_HOOK_URL:?BACKUP_HOOK_URL is required for provider-hook mode}"

    backup_payload="$(python3 - <<EOF
import json
print(json.dumps({
    "database_name": "${DB_NAME}",
    "backup_file": "${BACKUP_FILE}",
    "mode": "provider-hook",
}))
EOF
)"

    echo "Provider hook target: ${BACKUP_HOOK_URL}"

    if [[ "${DRY_RUN}" == "true" ]]; then
      echo "Dry run enabled. Provider hook payload: ${backup_payload}"
      exit 0
    fi

    curl_args=(
      --fail
      --show-error
      --silent
      --request POST
      --header "Content-Type: application/json"
      --data "${backup_payload}"
    )

    if [[ -n "${BACKUP_HOOK_TOKEN:-}" ]]; then
      curl_args+=(--header "Authorization: Bearer ${BACKUP_HOOK_TOKEN}")
    fi

    curl "${curl_args[@]}" "${BACKUP_HOOK_URL}"
    echo "Provider backup hook accepted."
    exit 0
    ;;
  *)
    echo "BACKUP_MODE must be one of: local-docker, direct, provider-hook." >&2
    exit 1
    ;;
esac

if [[ ! -s "${BACKUP_FILE}" ]]; then
  echo "Backup file is missing or empty: ${BACKUP_FILE}" >&2
  exit 1
fi

echo "Backup completed: ${BACKUP_FILE}"
