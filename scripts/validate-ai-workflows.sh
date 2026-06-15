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
  ".ai-rules/model-routing.md"
  ".claude/agents/code-reviewer.md"
  ".claude/hooks/codex-stop-review.sh"
  "scripts/ai/invoke-cross-reviewer.sh"
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

if [[ ! -x "$ROOT/scripts/ai/invoke-cross-reviewer.sh" ]]; then
  echo "validate-ai-workflows: scripts/ai/invoke-cross-reviewer.sh is not executable" >&2
  missing=1
fi

if [[ ! -x "$ROOT/.claude/hooks/codex-stop-review.sh" ]]; then
  echo "validate-ai-workflows: .claude/hooks/codex-stop-review.sh is not executable" >&2
  missing=1
fi

cross_provider_refs=(
  "AGENTS.md:scripts/ai/invoke-cross-reviewer.sh"
  "CLAUDE.md:scripts/ai/invoke-cross-reviewer.sh"
  ".ai-rules/agent-orchestration.md:.ai-rules/model-routing.md"
  ".ai-rules/agent-orchestration.md:scripts/ai/invoke-cross-reviewer.sh"
  ".ai-rules/model-routing.md:AI_REVIEW_MODEL"
  "scripts/ai/invoke-cross-reviewer.sh:AI_REVIEW_MODEL"
  "scripts/ai/invoke-cross-reviewer.sh:AI_REVIEW_TIER"
  "scripts/ai/invoke-cross-reviewer.sh:default_model_for_tier"
  ".ai-rules/model-routing.md:default_model_for_tier"
)

for entry in "${cross_provider_refs[@]}"; do
  file="${entry%%:*}"
  term="${entry#*:}"
  if ! grep -F "$term" "$ROOT/$file" >/dev/null; then
    echo "validate-ai-workflows: $file does not reference $term" >&2
    missing=1
  fi
done

two_agent_doc="$ROOT/docs/two-agent-review-workflow.md"
if ! grep -F "invoke-cross-reviewer.sh claude" "$two_agent_doc" >/dev/null; then
  echo "validate-ai-workflows: docs/two-agent-review-workflow.md missing Codex -> Claude review (invoke-cross-reviewer.sh claude)" >&2
  missing=1
fi
if ! grep -F "invoke-cross-reviewer.sh codex" "$two_agent_doc" >/dev/null; then
  echo "validate-ai-workflows: docs/two-agent-review-workflow.md missing Claude -> Codex review (invoke-cross-reviewer.sh codex)" >&2
  missing=1
fi

if [[ "$missing" -ne 0 ]]; then
  exit 1
fi

echo "validate-ai-workflows: all required AI workflow files present"
