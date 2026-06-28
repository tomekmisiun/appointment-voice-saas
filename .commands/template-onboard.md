# Command: Template Onboard

Copy everything below the line into your agent chat.

---

Help me use FastAPI Production Foundation as a fresh project.

**New product name:**  
<PASTE e.g. example-app>

**Domain (one line):**  
<PASTE what the product will build on top of the template>

**Modules to keep (default: all):**  
auth, multi-tenancy, workers, uploads, webhooks, audit logs — adjust if needed

**Instructions:**

1. Follow `.ai-rules/template-onboarding.md` and `agents/template-onboarding-agent.md`.
2. Read `docs/archive/legacy/template-onboarding.md`, `docs/archive/legacy/template-usage.md`, `docs/archive/legacy/template-freeze-checklist-root.md`.
3. Produce a concrete checklist: rename targets, env vars, validation commands, docs to edit in the fork.
4. Do **not** remove modules or change runtime code unless I explicitly asked to disable a module.
5. Run or instruct: `make bootstrap`, `make validate`, `make validate-ai-workflows` after config changes.

Output: onboarding checklist + suggested first domain implementation slice.
