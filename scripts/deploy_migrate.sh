#!/usr/bin/env bash
set -euo pipefail

IMAGE_REF="${IMAGE_REF:?IMAGE_REF is required}"
DATABASE_URL="${DATABASE_URL:?DATABASE_URL is required}"
ENVIRONMENT="${ENVIRONMENT:?ENVIRONMENT is required}"
DRY_RUN="${DRY_RUN:-false}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "Dry run enabled. Skipping Alembic migration."
  exit 0
fi

echo "Running Alembic upgrade head with ${IMAGE_REF}"

docker run --rm \
  -e DATABASE_URL="${DATABASE_URL}" \
  -e SECRET_KEY="${MIGRATION_SECRET_KEY:-migration-runner-secret-key-with-32-chars}" \
  -e ENVIRONMENT="${ENVIRONMENT}" \
  "${IMAGE_REF}" \
  alembic upgrade head

echo "Database migration completed."
