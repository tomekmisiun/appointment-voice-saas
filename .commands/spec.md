# Command: Create Feature Spec

Copy everything below the line into your agent chat.

---

You are working in the fastapi-production-foundation FastAPI repository.

Create a **feature spec** for the following work:

**Work request:**  
<PASTE USER REQUEST OR ROADMAP ITEM HERE>

**Instructions:**

1. Read `.ai-rules/agent-orchestration.md`, `.ai-rules/spec-driven-development.md`, and `.ai-rules/context-map.md` for the relevant task type.
2. Inspect existing code and tests before proposing changes.
3. Produce a spec with these sections:
   - Objective
   - Problem / user story
   - Requirements (numbered, testable)
   - Non-goals
   - Acceptance criteria
   - Impacted files (paths)
   - Risks (security, tenancy, migrations, deploy)
   - Verification plan (`make validate`, targeted pytest)
   - Open questions (only if blocking)
4. Do **not** implement code yet unless the user also asked to build it.
5. If the work is large, suggest saving the spec as `docs/specs/<slug>.md`.

Output the spec in markdown. Keep it concise and specific to this template's architecture.
