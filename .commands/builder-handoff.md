# Command: Builder Handoff (Builder Agent)

Use this format when the Builder Agent has finished implementation and is ready
to pass work to the Reviewer Agent.

---

You are the **Builder Agent** in the two-agent workflow for this repository.

**Mode:** produce a structured review handoff only. Do not commit, merge, push,
or delete branches unless the user explicitly writes `approve`.

## Before you write the handoff

1. Confirm you are on a **feature branch** (not `main` unless the user explicitly
   requested work on `main`).
2. Gather facts from the repository — do not invent paths, test counts, or results.
3. Run applicable validation (see `.ai-rules/agent-orchestration.md`):
   - App / tests / migrations → `make validate`
   - CI / scripts / AI workflow files → `make policy-guards` and
     `make validate-ai-workflows`
4. Collect:
   - `git branch --show-current`
   - `git diff --name-status main...HEAD` (or user-specified base)
   - `git diff main...HEAD` (attach or summarize; Reviewer may run locally)

## Rules (mandatory)

- **Do not claim validation passed** unless you actually ran the command and it
  exited successfully. Paste key output lines or summarize accurately.
- If validation was **skipped** or **failed**, state that clearly — do not
  imply green CI.
- **Do not hide risks.** List known gaps, untested paths, and follow-ups.
- **Do not commit, merge, push, or delete branches** unless the user explicitly
  writes `approve`.
- **Do not ask the Reviewer Agent to modify code immediately.** The Reviewer
  reviews first and returns a verdict (see `.commands/two-agent-review.md`).
- AI review is **advisory**; CI, tests, branch protection, and human approval
  remain the merge gate.

## Output format

Produce exactly this structure. Use `None` or `No change` where a section does not
apply — do not omit sections.

```markdown
## Builder handoff

### Objective
<One sentence: what this branch achieves>

### Branch
- **Branch name:** `<output of git branch --show-current>`
- **Base branch:** `main` (or user-specified base)

### Summary of implementation
<3–8 sentences: what was built, key design choices, scope boundaries>

### Files changed
<Paste `git diff --name-status main...HEAD` or equivalent>

### Diff
<Paste `git diff main...HEAD`, or state "Reviewer should run locally" if too large>

### Validation commands run
| Command | Run? |
|---------|------|
| `make validate` | Yes / No / N/A |
| `make policy-guards` | Yes / No / N/A |
| `make validate-ai-workflows` | Yes / No / N/A |

### Validation results
<Per command: PASS / FAIL / SKIPPED + brief evidence — test count, coverage, errors>

### Tests added or changed
<List test modules or "None">

### Database / migration impact
<New Alembic revision, model changes, index changes, or "None">

### API contract impact
<New/changed routes, schemas, status codes, versioning, or "None">

### Auth / authorization impact
<Permissions, roles, token behavior, or "None">

### Tenant isolation impact
<tenant_id scoping, cross-tenant paths, or "None">

### Security impact
<Secrets, validators, uploads, webhooks, rate limits, or "None">

### Docker / Compose / CI impact
<Dockerfile, workflows, Makefile, policy scripts, or "None">

### Observability / logging / metrics impact
<Metrics, structured logs, request IDs, or "None">

### Documentation impact
<README, docs/, tracking files, or "None">

### Known risks
<Bullet list — include validation gaps and deployment concerns>

### Reviewer focus areas
<Bullet list — where you want extra scrutiny, e.g. tenancy tests, migration rollback>

### Reviewer routing
For Codex CLI and Claude Code, do not ask the user to paste this handoff into a
new session. The Builder must automatically invoke the configured read-only
Reviewer subagent before the final response.

If a user explicitly asks for manual review, use this handoff with
`.commands/two-agent-review.md`.
```

After outputting or preparing the handoff, run the configured Reviewer subagent
when `.ai-rules/agent-orchestration.md` requires review.

Reference: `docs/two-agent-review-workflow.md`
