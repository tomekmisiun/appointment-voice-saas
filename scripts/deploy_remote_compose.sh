#!/usr/bin/env bash
set -euo pipefail

REMOTE_APP_DIR="${REMOTE_APP_DIR:?REMOTE_APP_DIR is required}"
IMAGE_REF="${IMAGE_REF:?IMAGE_REF is required}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

cd "${REMOTE_APP_DIR}"

export API_IMAGE="${IMAGE_REF}"

echo "Pulling ${API_IMAGE}"
docker pull "${API_IMAGE}"

echo "Applying compose changes from ${REMOTE_APP_DIR}"
docker compose -f docker-compose.prod.yml up -d api worker

if [[ "${RUN_MIGRATIONS}" == "true" ]]; then
  echo "Running Alembic migrations"
  docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
fi

echo "Remote compose deployment completed."
