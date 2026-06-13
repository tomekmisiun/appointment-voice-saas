#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
DEV_ADMIN_EMAIL="${DEV_ADMIN_EMAIL:-admin@example.local}"
DEV_PASSWORD="${DEV_PASSWORD:-devpassword123}"

request() {
  curl --fail --show-error --silent "$@"
}

echo "Checking liveness at ${API_BASE_URL}/health"
request "${API_BASE_URL}/health" | grep -q '"status":"ok"'

echo "Checking readiness at ${API_BASE_URL}/health/ready"
request "${API_BASE_URL}/health/ready" | grep -q '"status":"ok"'

echo "Logging in as ${DEV_ADMIN_EMAIL}"
login_response="$(
  request \
    --request POST \
    --header "Content-Type: application/json" \
    --data "{\"email\":\"${DEV_ADMIN_EMAIL}\",\"password\":\"${DEV_PASSWORD}\"}" \
    "${API_BASE_URL}/api/v1/auth/login"
)"

access_token="$(
  python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])' \
    <<<"${login_response}"
)"

echo "Checking authenticated profile at ${API_BASE_URL}/api/v1/auth/me"
me_response="$(
  request \
    --header "Authorization: Bearer ${access_token}" \
    "${API_BASE_URL}/api/v1/auth/me"
)"

python3 -c 'import json, sys; payload=json.load(sys.stdin); assert payload["email"]' \
  <<<"${me_response}" >/dev/null

echo "Smoke checks passed."
