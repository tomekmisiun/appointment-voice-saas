#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/ci/_lib.sh
source "$ROOT/scripts/ci/_lib.sh"

errors=()
base_ref="$(resolve_base_ref)"
workflow_diff="$(git diff "$base_ref...HEAD" -- .github/workflows || true)"
current_ci="$ROOT/.github/workflows/ci.yml"
dep_review="$ROOT/.github/workflows/dependency-review.yml"

if [ -n "$workflow_diff" ]; then
  if grep -Eq '^-.*--cov-fail-under=[0-9]+' <<<"$workflow_diff"; then
    if ! grep -Eq '^\+.*--cov-fail-under=[0-9]+' <<<"$workflow_diff"; then
      errors+=("removed pytest coverage floor from CI workflows")
    else
      removed_floor="$(grep -Eo '[0-9]+$' <<<"$(grep -Eo '^-.*--cov-fail-under=[0-9]+' <<<"$workflow_diff" | tail -1)")"
      added_floor="$(grep -Eo '[0-9]+$' <<<"$(grep -Eo '^\+.*--cov-fail-under=[0-9]+' <<<"$workflow_diff" | tail -1)")"
      if [ -n "$removed_floor" ] && [ -n "$added_floor" ] && [ "$added_floor" -lt "$removed_floor" ]; then
        errors+=("lowered pytest coverage floor from ${removed_floor} to ${added_floor}")
      fi
    fi
  fi

  if grep -Fq 'trivy-action' <<<"$workflow_diff"; then
    if grep -Eq '^-.*exit-code: "1"' <<<"$workflow_diff" && ! grep -Eq '^\+.*exit-code: "1"' <<<"$workflow_diff"; then
      errors+=("removed blocking Trivy exit-code policy")
    fi
  fi

  if grep -Eq '^-.*pip-audit' <<<"$workflow_diff" && ! grep -Eq '^\+.*pip-audit' <<<"$workflow_diff"; then
    errors+=("removed dependency vulnerability gate (pip-audit)")
  fi

  if grep -Eq '^-  test:' <<<"$workflow_diff" && ! grep -Eq '^\+  test:' <<<"$workflow_diff"; then
    errors+=("removed required test job from CI")
  fi
fi

if [ -f "$current_ci" ]; then
  if ! grep -Fq -- '--cov-fail-under=85' "$current_ci"; then
    errors+=("ci.yml must keep --cov-fail-under=85")
  fi
  if ! grep -Fq 'exit-code: "1"' "$current_ci"; then
    errors+=("ci.yml must keep blocking Trivy exit-code: \"1\"")
  fi
  if ! grep -Eq '^  test:' "$current_ci"; then
    errors+=("ci.yml must keep the test job")
  fi
  if grep -Fq 'docker-build:' "$current_ci"; then
    docker_block="$(awk '/^  docker-build:/{p=1} p{print} p && /^  [a-zA-Z0-9_-]+:/ && !/^  docker-build:/{exit}' "$current_ci")"
    if ! grep -A5 '^    needs:' <<<"$docker_block" | grep -Fq 'test'; then
      errors+=("docker-build job must declare needs: [test]")
    fi
  fi
fi

if [ -f "$dep_review" ]; then
  if ! grep -Fq 'pip-audit' "$dep_review"; then
    errors+=("dependency-review.yml must keep a pip-audit (or equivalent) vulnerability gate")
  fi
  audit_block="$(awk '/uses: pypa\/gh-action-pip-audit/{p=1} p{print; if (/^$/) exit}' "$dep_review")"
  if grep -Fq 'continue-on-error: true' <<<"$audit_block"; then
    errors+=("dependency-review.yml pip-audit step must not be continue-on-error")
  fi
fi

if [ "${#errors[@]}" -eq 0 ]; then
  echo "ci-gate-regression: ok"
  exit 0
fi

cat <<EOF
ERROR: CI gate regression detected:

EOF
printf '  - %s\n' "${errors[@]}"
cat <<EOF

Restore the guard or document an intentional change in the PR description.

See docs/development/ci-policy.md
EOF
exit 1
