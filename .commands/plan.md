# Command: Plan Tasks

Copy everything below the line into your agent chat.

---

You are working in the fastapi-production-foundation FastAPI repository.

Break the following work into **small, verifiable tasks**:

**Input (spec, roadmap item, or description):**  
<PASTE HERE>

**Instructions:**

1. Read `.ai-rules/planning-and-task-breakdown.md` and `.ai-rules/incremental-work.md`.
2. Use the task card format: title, scope, acceptance criteria, likely files, validation command, dependencies, rollback/safety.
3. Order tasks for safe implementation (migration → service → route → tests → docs).
4. Prefer **one roadmap/tech-debt item per PR** when applicable.
5. Map TECH_DEBT IDs if the input references ROADMAP rows.
6. Do not implement yet unless asked.

Output a numbered task list ready for sequential execution.
