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
  ".ai-rules/learning-mode.md"
  ".ai-rules/tdd-and-regression.md"
  ".ai-rules/review.md"
  ".ai-rules/review-checklist.md"
  ".ai-rules/threat-modeling.md"
  ".codex/agents/reviewer.toml"
  ".claude/agents/code-reviewer.md"
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

learning_docs=(
  "docs/learning/README.md"
  "docs/learning/00-current-state-audit.md"
  "docs/learning/01-system-mental-map.md"
  "docs/learning/02-file-by-file-map.md"
  "docs/learning/03-request-flow-map.md"
  "docs/learning/04-domain-model-map.md"
  "docs/learning/05-how-to-change-common-things.md"
  "docs/learning/06-interview-defense-guide.md"
)

for file in "${learning_docs[@]}"; do
  if [[ ! -f "$ROOT/$file" ]]; then
    echo "validate-ai-workflows: missing learning doc: $file" >&2
    missing=1
  fi
done

runner_terms=(
  "make ai-two-agent"
  "make ai-review"
  ".ai-runs"
  "scripts/ai-two-agent.sh"
  "scripts/ai-review-latest.sh"
)

runner_scan_paths=(
  "AGENTS.md"
  "CLAUDE.md"
  ".ai-rules"
  ".commands"
  "docs"
  "Makefile"
  ".gitignore"
)

for term in "${runner_terms[@]}"; do
  if grep -R --exclude-dir=foundation --exclude-dir=.git -F "$term" \
    "${runner_scan_paths[@]/#/$ROOT/}" >/dev/null; then
    echo "validate-ai-workflows: stale local runner reference: $term" >&2
    missing=1
  fi
done

reviewer_headings=(
  "## Blockers"
  "## Should-fix"
  "## Nice-to-have"
  "## Validation concerns"
  "## Security/production risks"
  "## Overengineering/scope creep"
  "## Final verdict"
)

for heading in "${reviewer_headings[@]}"; do
  if ! grep -F "$heading" "$ROOT/.ai-rules/review-checklist.md" >/dev/null; then
    echo "validate-ai-workflows: missing reviewer heading: $heading" >&2
    missing=1
  fi
done

approve_gate_files=(
  ".ai-rules/git.md"
  ".ai-rules/agent-orchestration.md"
  "docs/two-agent-review-workflow.md"
)

for file in "${approve_gate_files[@]}"; do
  if ! grep -F "approve" "$ROOT/$file" >/dev/null; then
    echo "validate-ai-workflows: missing approve gate: $file" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "validate-ai-workflows: all required AI workflow files present"
