#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

bash "$ROOT/scripts/ci/check_model_migration_pair.sh"
bash "$ROOT/scripts/ci/check_pyproject_lock_pair.sh"
bash "$ROOT/scripts/ci/check_migration_drops.sh"
bash "$ROOT/scripts/ci/check_ci_gate_regression.sh"
bash "$ROOT/scripts/ci/check_no_ai_commit_trailers.sh"
bash "$ROOT/scripts/validate-ai-workflows.sh"

echo "policy-guards: all checks passed"
