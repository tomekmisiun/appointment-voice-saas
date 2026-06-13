#!/usr/bin/env bash
set -euo pipefail

ENVIRONMENT="${ENVIRONMENT:?ENVIRONMENT is required}"
IMAGE_REF="${IMAGE_REF:?IMAGE_REF is required}"
DRY_RUN="${DRY_RUN:-false}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"

if [[ "${ENVIRONMENT}" != "staging" && "${ENVIRONMENT}" != "production" ]]; then
  echo "ENVIRONMENT must be staging or production." >&2
  exit 1
fi

if [[ "${ENVIRONMENT}" == "production" && "${IMAGE_REF##*:}" == "latest" ]]; then
  if [[ "${ALLOW_LATEST_PRODUCTION:-false}" != "true" ]]; then
    echo "Refusing to deploy the latest tag to production." >&2
    echo "Use an immutable release tag or commit SHA, or set ALLOW_LATEST_PRODUCTION=true." >&2
    exit 1
  fi
fi

if [[ "${RUN_MIGRATIONS}" == "true" ]]; then
  run_migrations_json="True"
else
  run_migrations_json="False"
fi

promotion_payload="$(python3 - <<EOF
import json
print(json.dumps({
    "environment": "${ENVIRONMENT}",
    "image": "${IMAGE_REF}",
    "run_migrations": ${run_migrations_json},
}))
EOF
)"

echo "Promotion target: ${ENVIRONMENT}"
echo "Image reference: ${IMAGE_REF}"
echo "Run migrations: ${RUN_MIGRATIONS}"

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "Dry run enabled. No deployment changes were applied."
  echo "Payload: ${promotion_payload}"
  exit 0
fi

if [[ -n "${DEPLOY_HOOK_URL:-}" ]]; then
  echo "Triggering deployment hook."
  curl_args=(
    --fail
    --show-error
    --silent
    --request POST
    --header "Content-Type: application/json"
    --data "${promotion_payload}"
  )

  if [[ -n "${DEPLOY_HOOK_TOKEN:-}" ]]; then
    curl_args+=(--header "Authorization: Bearer ${DEPLOY_HOOK_TOKEN}")
  fi

  curl "${curl_args[@]}" "${DEPLOY_HOOK_URL}"
  echo "Deployment hook accepted."
  exit 0
fi

if [[ -n "${DEPLOY_SSH_HOST:-}" ]]; then
  echo "Promoting image over SSH."
  REMOTE_APP_DIR="${REMOTE_APP_DIR:?REMOTE_APP_DIR is required for SSH deployment}"
  DEPLOY_SSH_USER="${DEPLOY_SSH_USER:?DEPLOY_SSH_USER is required for SSH deployment}"

  ssh_args=(
    -o BatchMode=yes
    -o StrictHostKeyChecking=accept-new
  )

  if [[ -n "${DEPLOY_SSH_PRIVATE_KEY:-}" ]]; then
    key_file="$(mktemp)"
    trap 'rm -f "${key_file}"' EXIT
    printf '%s\n' "${DEPLOY_SSH_PRIVATE_KEY}" >"${key_file}"
    chmod 600 "${key_file}"
    ssh_args+=(-i "${key_file}")
  fi

  ssh "${ssh_args[@]}" "${DEPLOY_SSH_USER}@${DEPLOY_SSH_HOST}" \
    "REMOTE_APP_DIR=${REMOTE_APP_DIR} IMAGE_REF=${IMAGE_REF} RUN_MIGRATIONS=${RUN_MIGRATIONS} bash -s" \
    <"$(dirname "${BASH_SOURCE[0]}")/deploy_remote_compose.sh"

  if [[ -n "${GITHUB_ENV:-}" ]]; then
    echo "SKIP_RUNNER_MIGRATIONS=true" >>"${GITHUB_ENV}"
  fi

  echo "SSH deployment finished."
  exit 0
fi

echo "No deployment backend configured for ${ENVIRONMENT}." >&2
echo "Configure DEPLOY_HOOK_URL or DEPLOY_SSH_HOST in the GitHub environment." >&2
exit 1
