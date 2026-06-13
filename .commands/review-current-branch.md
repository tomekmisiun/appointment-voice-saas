# Command: Review Current Branch

Copy everything below the line into your agent chat.

---

You are reviewing the **current branch** before a PR in fastapi-production-foundation.

**Base branch:** main (unless user specified otherwise)

**Instructions:**

1. Read `.ai-rules/review.md` and load personas from `agents/` as needed:
   - Backend → `agents/backend-reviewer.md`
   - Security → `agents/security-auditor.md`
   - Tenancy → `agents/tenancy-reviewer.md`
   - DB → `agents/database-reviewer.md`
   - CI/Docker → `agents/devops-ci-reviewer.md`
2. Compare branch to base: `git diff main...HEAD` (or user-specified base).
3. Check architecture, tests, security, tenancy, migrations, docs/status consistency.
4. Run or recommend validation: `make validate` for app changes; `make policy-guards` + `make validate-ai-workflows` for CI/rules-only.
5. Verify commit messages on the branch contain no AI attribution trailers:
   `bash scripts/ci/check_no_ai_commit_trailers.sh` (also part of `make policy-guards`).
6. Do not fix code unless the user asked for fixes — review first.

**Output format:**

```markdown
## Summary
## Findings (table with Severity | File | Issue | Recommendation)
## Validation (commands + results)
## Verdict (Approve / Approve with nits / Request changes)
```

Be strict; prefer evidence over assumptions.
