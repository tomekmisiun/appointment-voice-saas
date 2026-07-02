#!/usr/bin/env bash
# Validates all required Railway production env vars before or after deploy.
# Run locally: bash scripts/railway-env-check.sh
# Run in Railway shell: railway run bash scripts/railway-env-check.sh
set -euo pipefail

FAIL=0

ok() { echo "OK      $1"; }
missing() { echo "MISSING $1"; FAIL=1; }
default_val() { echo "DEFAULT $1 (still using default '$2')"; FAIL=1; }

check() {
  local var="$1"
  local val="${!var:-}"
  if [[ -z "$val" ]]; then missing "$var"; else ok "$var"; fi
}

check_not() {
  local var="$1"
  local bad="$2"
  local val="${!var:-}"
  if [[ -z "$val" ]]; then missing "$var"
  elif [[ "$val" == "$bad" ]]; then default_val "$var" "$bad"
  else ok "$var"
  fi
}

echo "=== Railway Production Env Check ($(date -u +%Y-%m-%dT%H:%M:%SZ)) ==="

echo
echo "--- Core ---"
check SECRET_KEY
check_not DATABASE_URL "postgresql://app_user:app_password@db:5432/app_db"
check_not REDIS_HOST "redis"
check REDIS_PASSWORD

echo
echo "--- SMTP / Email ---"
check SMTP_HOST
check SMTP_USERNAME
check SMTP_PASSWORD
check_not EMAIL_FROM "noreply@example.com"
check_not PASSWORD_RESET_URL "http://localhost:8000/reset-password"

echo
echo "--- S3 / Object Storage ---"
check_not S3_ENDPOINT_URL "http://minio:9000"
check_not S3_ACCESS_KEY_ID "minioadmin"
check_not S3_SECRET_ACCESS_KEY "minioadmin"
check_not S3_BUCKET_NAME "uploads"

echo
echo "--- Security ---"
check WEBHOOK_SIGNATURE_SECRET
check METRICS_BEARER_TOKEN
check TRUSTED_HOSTS
check_not TRUSTED_HOSTS_ENABLED "false"
check_not RATE_LIMIT_TRUST_FORWARDED_HEADERS "false"

echo
echo "--- Malware scan (required in production) ---"
check_not UPLOAD_MALWARE_SCAN_ENABLED "false"
check UPLOAD_MALWARE_SCANNER_URL

echo
echo "--- Twilio (if any voice/SMS is configured) ---"
# These are validated together by Settings.validate_production_settings.
if [[ -n "${TWILIO_ACCOUNT_SID:-}${TWILIO_SMS_FROM:-}${TWILIO_VOICE_NUMBER:-}${TWILIO_VOICE_BASE_URL:-}" ]]; then
  check TWILIO_AUTH_TOKEN
else
  echo "SKIP    TWILIO_AUTH_TOKEN (no Twilio vars set)"
fi

echo
echo "--- Public demo (optional) ---"
if [[ "${PUBLIC_DEMO_ENABLED:-false}" == "true" ]]; then
  check PUBLIC_DEMO_USER_EMAIL
  check PUBLIC_DEMO_BUSINESS_ID
else
  echo "SKIP    PUBLIC_DEMO_* (PUBLIC_DEMO_ENABLED is not true)"
fi

echo
if [[ $FAIL -eq 1 ]]; then
  echo "=== FAILED: one or more required variables are missing or using local defaults ==="
  echo "    Fix them in your Railway service environment before deploying."
  exit 1
else
  echo "=== PASSED: all production env variables look configured ==="
fi
