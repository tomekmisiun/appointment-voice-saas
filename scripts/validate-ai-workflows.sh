#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

required_files=(
  "AGENTS.md"
  "CLAUDE.md"
  "docs/ai-workflows.md"
  "docs/two-agent-review-workflow.md"
  ".ai-rules/agent-orchestration.md"
  ".ai-rules/anti-overengineering.md"
  ".ai-rules/context-map.md"
  ".ai-rules/template-onboarding.md"
  ".ai-rules/spec-driven-development.md"
  ".ai-rules/planning-and-task-breakdown.md"
  ".ai-rules/incremental-work.md"
  ".ai-rules/tdd-and-regression.md"
  ".ai-rules/review.md"
  ".ai-rules/threat-modeling.md"
)

required_dirs=(
  "agents"
  ".commands"
  "docs/specs"
)

missing=0

for file in "${required_files[@]}"; do
  if [[ ! -f "$ROOT/$file" ]]; then
    echo "validate-ai-workflows: missing file: $file" >&2
    missing=1
  fi
done

for dir in "${required_dirs[@]}"; do
  if [[ ! -d "$ROOT/$dir" ]]; then
    echo "validate-ai-workflows: missing directory: $dir" >&2
    missing=1
  fi
done

command_files=(
  ".commands/spec.md"
  ".commands/plan.md"
  ".commands/build-next-roadmap-task.md"
  ".commands/review-current-branch.md"
  ".commands/builder-handoff.md"
  ".commands/two-agent-review.md"
  ".commands/security-audit.md"
  ".commands/template-onboard.md"
  ".commands/update-project-status.md"
)

for file in "${command_files[@]}"; do
  if [[ ! -f "$ROOT/$file" ]]; then
    echo "validate-ai-workflows: missing command: $file" >&2
    missing=1
  fi
done

agent_files=(
  "agents/backend-reviewer.md"
  "agents/security-auditor.md"
  "agents/tenancy-reviewer.md"
  "agents/database-reviewer.md"
  "agents/devops-ci-reviewer.md"
  "agents/template-onboarding-agent.md"
)

for file in "${agent_files[@]}"; do
  if [[ ! -f "$ROOT/$file" ]]; then
    echo "validate-ai-workflows: missing persona: $file" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "validate-ai-workflows: all required AI workflow files present"
