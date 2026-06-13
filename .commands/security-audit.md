# Command: Security Audit

Copy everything below the line into your agent chat.

---

Perform a **security review** of fastapi-production-foundation.

**Scope:**  
<REPO FULL | CURRENT BRANCH DIFF | SPECIFIC AREA e.g. auth, uploads, webhooks>

**Instructions:**

1. Read `.ai-rules/security.md`, `.ai-rules/threat-modeling.md`, and `agents/security-auditor.md`.
2. Inspect code, tests, config validators, and relevant docs — not assumptions.
3. For each finding: trust boundary, abuse case, severity, evidence (file/path), recommended fix or test.
4. Distinguish template-scope gaps (tracked in TECH_DEBT P3) from regressions in current diff.
5. Suggest targeted tests and run `make validate` if you change code (only if user asked to fix).

**Severity:** Critical | High | Medium | Low

**Output:**

```markdown
## Security audit summary
## Scope
## Findings (table)
## Tests / validation gaps
## Verdict
```

Do not expand scope into new features.
