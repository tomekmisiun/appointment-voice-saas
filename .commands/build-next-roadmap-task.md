# Command: Build Next Roadmap Task

Copy everything below the line into your agent chat.

---

You are working in the fastapi-production-foundation FastAPI repository.

Implement the **next safe roadmap or TECH_DEBT task** unless the user named a specific item.

**Optional target:**  
<PASTE ROADMAP # OR TD-ID, OR LEAVE EMPTY FOR NEXT IN PRIORITY ORDER>

**Instructions:**

1. Read `ROADMAP.md`, `TECH_DEBT.md`, `PROJECT_STATUS.md` — do not duplicate planned work as "done".
2. Follow `.ai-rules/agent-orchestration.md` → spec (if non-trivial) → plan → incremental slices.
3. Create a feature branch; one task per PR.
4. Implement with tests; run targeted pytest then `make validate`.
5. Update `ROADMAP.md` / `TECH_DEBT.md` / `PROJECT_STATUS.md` / README only when behavior or verified capabilities change.
6. Do **not** commit, push, or merge unless the user explicitly asks.
7. When committing: verify the exact message has **no** AI attribution trailers
   (`Co-authored-by: Cursor`, `Claude`, `Codex`, `Generated-by:`, `Created-by: AI`).
   Run `bash scripts/ci/check_no_ai_commit_trailers.sh --message-file <file>` or
   `make policy-guards` before push. See `.ai-rules/git.md`.
8. Report: files changed, tests run, validation result, risks, remaining work.

If the next item is P3 optional or doc-only, state that and proceed only if it is clearly safe and requested.
